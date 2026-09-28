"""GUI-state regression checks. Run with Python containing Tk: python -m unittest -v test_app."""
import io
import json
import os
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

import app


class FakeProcess:
    def __init__(self):
        self.returncode = None
        self.terminated = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = 1

    def wait(self):
        return self.returncode


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dimascript-test-')
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.env = patch.dict(os.environ, {'LOCALAPPDATA': self.temp.name})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.destroy_root)
        self.gui = app.App(self.root, test_mode=True)

    def destroy_root(self):
        for callback in self.root.tk.call('after', 'info'):
            self.root.after_cancel(callback)
        self.root.destroy()

    def make_running(self):
        self.gui.output = self.directory / 'result'
        self.gui.output.mkdir()
        self.gui.process = FakeProcess()
        self.gui.log = io.StringIO()
        self.gui.set_busy(True)
        self.gui.open_button.configure(state='normal')

    def dispatch(self, *events):
        for event in events:
            self.gui.events.put(event)
        self.gui.poll()

    def test_empty_paths_never_create_output_or_launch(self):
        for source, destination in [('', str(self.directory)), (' ', str(self.directory)), ('file.wav', '')]:
            with self.subTest(source=source, destination=destination):
                self.gui.source.set(source)
                self.gui.destination.set(destination)
                with patch('tkinter.messagebox.showerror') as error, patch.object(app.subprocess, 'Popen') as process:
                    self.gui.start()
                error.assert_called_once()
                process.assert_not_called()
                self.assertIsNone(self.gui.output)

    def test_missing_source_does_not_create_destination(self):
        destination = self.directory / 'not-created'
        self.gui.source.set(str(self.directory / 'missing.wav'))
        self.gui.destination.set(str(destination))
        with patch('tkinter.messagebox.showerror') as error:
            self.gui.start()
        error.assert_called_once()
        self.assertFalse(destination.exists())

    def test_destination_file_is_rejected_before_process(self):
        source = self.directory / 'input.wav'
        source.write_bytes(b'test')
        self.gui.source.set(str(source))
        self.gui.destination.set(str(source))
        with patch('tkinter.messagebox.showerror') as error, patch.object(app.subprocess, 'Popen') as process:
            self.gui.start()
        error.assert_called_once()
        process.assert_not_called()
        self.assertFalse(self.gui.start_button.instate(['disabled']))

    def test_process_launch_failure_closes_log(self):
        source = self.directory / 'input.wav'
        source.write_bytes(b'test')
        self.gui.source.set(str(source))
        self.gui.destination.set(str(self.directory / 'new-output'))
        with patch('tkinter.messagebox.showerror') as error, patch.object(app.subprocess, 'Popen', side_effect=OSError('launch failed')):
            self.gui.start()
        error.assert_called_once()
        self.assertIsNone(self.gui.process)
        self.assertTrue(self.gui.log.closed)
        self.assertFalse(self.gui.start_button.instate(['disabled']))

    def test_repeated_launch_failure_preserves_previous_result(self):
        self.make_running()
        old_output = self.gui.output
        final = old_output / 'Транскрипция.txt'
        final.write_text('Предыдущая запись', encoding='utf-8')
        self.dispatch({'kind': 'done', 'count': 1}, {'kind': 'exit', 'code': 0})
        source = self.directory / 'second.wav'
        source.write_bytes(b'test')
        self.gui.source.set(str(source))
        self.gui.destination.set(str(self.directory))
        with patch('tkinter.messagebox.showerror') as error, patch.object(app.subprocess, 'Popen', side_effect=OSError('launch failed')):
            self.gui.start()
        error.assert_called_once()
        self.assertIsNone(self.gui.process)
        self.assertEqual(self.gui.output, old_output)
        self.assertEqual(self.gui.result_text(), final)
        self.assertEqual(final.read_text(encoding='utf-8'), 'Предыдущая запись')
        self.assertFalse(self.gui.text_button.instate(['disabled']))

    def test_progress_does_not_claim_completion_and_updates_preview(self):
        self.make_running()
        self.dispatch({'kind': 'progress', 'position': 100, 'duration': 100, 'text': 'Проверка кириллицы.'})
        self.assertEqual(float(self.gui.bar['value']), 99)
        self.assertFalse(self.gui.completed)
        self.assertIn('Проверка кириллицы.', self.gui.preview.get('1.0', 'end'))
        self.assertTrue(self.gui.start_button.instate(['disabled']))

    def test_done_enables_result_actions_after_exit(self):
        self.make_running()
        (self.gui.output / 'Транскрипция.txt').write_text('Результат', encoding='utf-8')
        self.dispatch({'kind': 'done', 'count': 1}, {'kind': 'exit', 'code': 0})
        self.assertTrue(self.gui.completed)
        self.assertEqual(float(self.gui.bar['value']), 100)
        self.assertIsNone(self.gui.process)
        self.assertTrue(self.gui.log.closed)
        self.assertFalse(self.gui.copy_button.instate(['disabled']))
        self.assertFalse(self.gui.text_button.instate(['disabled']))
        self.assertTrue(self.gui.stop_button.instate(['disabled']))
        self.assertIn('завершена', self.gui.status.get())

    def test_no_speech_is_finished_with_distinct_status(self):
        self.make_running()
        (self.gui.output / 'Транскрипция.txt').write_text('Речь не обнаружена.', encoding='utf-8')
        self.dispatch({'kind': 'done', 'count': 0}, {'kind': 'exit', 'code': 0})
        self.assertTrue(self.gui.completed)
        self.assertEqual(float(self.gui.bar['value']), 100)
        self.assertEqual(self.gui.status.get(), 'Речь не обнаружена')

    def test_stop_keeps_partial_and_restores_controls(self):
        self.make_running()
        partial = self.gui.output / 'Транскрипция.partial.txt'
        partial.write_text('Сохранённая фраза', encoding='utf-8')
        process = self.gui.process
        self.gui.stop()
        self.assertTrue(process.terminated)
        self.assertTrue(self.gui.cancelled)
        self.dispatch({'kind': 'exit', 'code': 1})
        self.assertFalse(self.gui.completed)
        self.assertEqual(partial.read_text(encoding='utf-8'), 'Сохранённая фраза')
        self.assertFalse(self.gui.copy_button.instate(['disabled']))
        self.assertFalse(self.gui.start_button.instate(['disabled']))
        self.assertIn('Частичный', self.gui.progress_text.get())

    def test_stop_before_speech_does_not_offer_missing_text(self):
        self.make_running()
        self.gui.bar.configure(mode='indeterminate')
        self.gui.stop()
        self.dispatch({'kind': 'exit', 'code': 1})
        self.assertTrue(self.gui.text_button.instate(['disabled']))
        self.assertEqual(str(self.gui.bar['mode']), 'determinate')
        self.assertEqual(float(self.gui.bar['value']), 0)
        self.assertIn('не успело', self.gui.progress_text.get())

    def test_error_preserves_partial_and_does_not_claim_success(self):
        self.make_running()
        partial = self.gui.output / 'Транскрипция.partial.txt'
        partial.write_text('Частичный текст', encoding='utf-8')
        self.dispatch({'kind': 'exit', 'code': 1})
        self.assertFalse(self.gui.completed)
        self.assertIn('Не удалось', self.gui.status.get())
        self.assertIn('Диагностика.log', self.gui.progress_text.get())
        self.assertFalse(self.gui.copy_button.instate(['disabled']))
        self.assertEqual(self.gui.result_text(), partial)

    def test_result_text_prefers_final_and_ignores_missing_files(self):
        self.gui.output = self.directory
        self.assertIsNone(self.gui.result_text())
        partial = self.directory / 'Транскрипция.partial.txt'
        partial.write_text('partial', encoding='utf-8')
        self.assertEqual(self.gui.result_text(), partial)
        final = self.directory / 'Транскрипция.txt'
        final.write_text('final', encoding='utf-8')
        self.assertEqual(self.gui.result_text(), final)

    def test_test_mode_never_writes_settings(self):
        self.gui.save_settings()
        self.assertFalse(self.gui.settings_path.exists())

    def test_settings_persist_in_utf8_and_no_temporary_remains(self):
        self.gui.test_mode = False
        self.gui.source.set(str(self.directory / 'Лекция' / 'запись.mp4'))
        self.gui.destination.set(str(self.directory / 'Результаты'))
        self.gui.language.set('English')
        self.gui.save_settings()
        saved = json.loads(self.gui.settings_path.read_text(encoding='utf-8'))
        self.assertEqual(saved['language'], 'English')
        self.assertEqual(saved['destination'], self.gui.destination.get())
        self.assertEqual(saved['source_directory'], str(self.directory / 'Лекция'))
        self.assertEqual(list(self.gui.settings_path.parent.glob('*.tmp')), [])

    def test_settings_write_failure_does_not_crash(self):
        self.gui.test_mode = False
        with patch.object(app.os, 'replace', side_effect=PermissionError('read only')):
            self.gui.save_settings()
        self.assertFalse(self.gui.settings_path.exists())

    def test_corrupt_or_invalid_settings_do_not_crash_startup(self):
        settings = self.gui.settings_path
        settings.parent.mkdir()
        for content in ['{broken', '[]', '{"destination": 12, "language": "unknown"}']:
            with self.subTest(content=content):
                settings.write_text(content, encoding='utf-8')
                other = tk.Toplevel(self.root)
                other.withdraw()
                callbacks_before = set(other.tk.call('after', 'info'))
                try:
                    instance = app.App(other, test_mode=False)
                    self.assertEqual(instance.language.get(), 'Русский')
                    self.assertTrue(instance.destination.get().endswith('DimaScript'))
                finally:
                    for callback in set(other.tk.call('after', 'info')) - callbacks_before:
                        other.after_cancel(callback)
                    other.destroy()


class FileTests(unittest.TestCase):
    def test_same_timestamp_produces_distinct_output_folders(self):
        with tempfile.TemporaryDirectory(prefix='dimascript-test-') as directory:
            with patch.object(app, 'datetime') as clock:
                clock.now.return_value.strftime.return_value = '2026-09-26_12-00-00'
                first = app.create_run_folder(directory, 'Лекция')
                second = app.create_run_folder(directory, 'Лекция')
            self.assertNotEqual(first, second)
            self.assertTrue(first.is_dir())
            self.assertTrue(second.is_dir())
            self.assertTrue(second.name.endswith('_1'))

    def test_timecodes_round_carry_and_srt_separator(self):
        self.assertEqual(app.timestamp(59.9996), '00:01:00.000')
        self.assertEqual(app.timestamp(3661.25, srt=True), '01:01:01,250')
        self.assertEqual(app.timestamp(-1), '00:00:00.000')


if __name__ == '__main__':
    unittest.main()
