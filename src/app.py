"""DimaScript desktop transcription and isolated recognition worker."""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
from datetime import datetime

BASE = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent
MODEL_CACHE = BASE / 'models'
ASSETS = BASE if getattr(sys, 'frozen', False) else BASE / 'assets'


def timestamp(seconds, srt=False):
    ms = max(0, round(seconds * 1000))
    hours, ms = divmod(ms, 3600000)
    minutes, ms = divmod(ms, 60000)
    seconds, ms = divmod(ms, 1000)
    return f'{hours:02}:{minutes:02}:{seconds:02}{"," if srt else "."}{ms:03}'


def emit(kind, **values):
    print(json.dumps(dict(kind=kind, **values), ensure_ascii=False), flush=True)


def worker(source, destination, language):
    os.environ['HF_HUB_OFFLINE'] = '1'
    import av
    from faster_whisper import WhisperModel

    emit('stage', text='Проверка аудиодорожки…')
    with av.open(source) as media:
        if not media.streams.audio:
            raise ValueError('В выбранном файле нет аудиодорожки.')
    emit('stage', text='Загрузка локальной модели…')
    model = WhisperModel('small', device='cpu', compute_type='int8',
                         cpu_threads=min(8, os.cpu_count() or 4),
                         download_root=str(MODEL_CACHE), local_files_only=True)
    emit('stage', text='Чтение аудио и поиск речи — это может занять несколько минут…')
    segments, info = model.transcribe(source, language=None if language == 'auto' else language,
                                     beam_size=3, vad_filter=True,
                                     condition_on_previous_text=False)
    duration = info.duration
    output = Path(destination)
    txt = output / 'Транскрипция.partial.txt'
    srt = output / 'Субтитры.partial.srt'
    count = 0
    emit('progress', position=0, duration=duration, text='Распознавание речи…')
    with txt.open('w', encoding='utf-8-sig') as text_file, srt.open('w', encoding='utf-8-sig') as subtitle_file:
        text_file.write(f'Источник: {source}\nМодель: Whisper small; язык: {info.language}\n'
                        'Автоматическая транскрипция: возможны ошибки в именах и терминах.\n\n')
        text_file.flush()
        for segment in segments:
            text = segment.text.strip()
            if text:
                count += 1
                text_file.write(f'[{timestamp(segment.start)} — {timestamp(segment.end)}] {text}\n')
                subtitle_file.write(f'{count}\n{timestamp(segment.start, True)} --> '
                                    f'{timestamp(segment.end, True)}\n{text}\n\n')
                text_file.flush()
                subtitle_file.flush()
            emit('progress', position=segment.end, duration=duration, text=text)
        if not count:
            text_file.write('Речь не обнаружена.\n')
    txt.rename(output / 'Транскрипция.txt')
    srt.rename(output / 'Субтитры.srt')
    emit('done', folder=str(output), count=count)


def create_run_folder(destination, stem):
    name = stem[:90] + '_' + datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    for index in range(1000):
        path = Path(destination) / (name if index == 0 else f'{name}_{index}')
        try:
            path.mkdir()
            return path
        except FileExistsError:
            continue
    raise OSError('Не удалось создать отдельную папку результата.')


class App:
    def __init__(self, root, test_mode=False):
        import tkinter as tk
        from tkinter import ttk
        self.root = root
        self.test_mode = test_mode
        self.process = None
        self.events = queue.Queue()
        self.output = None
        self.completed = False
        self.cancelled = False
        self.stage = ''
        self.started = None
        self.settings_path = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'DimaScript' / 'settings.json'
        self.settings = {}
        if not test_mode:
            try:
                self.settings = json.loads(self.settings_path.read_text(encoding='utf-8'))
                if not isinstance(self.settings, dict):
                    self.settings = {}
            except (OSError, ValueError):
                pass
        self.settings = {key: value for key, value in self.settings.items()
                         if isinstance(value, str) and value.strip()}
        self.settings = {key: value for key, value in self.settings.items() if isinstance(value, str)}
        root.title('DimaScript')
        icon = ASSETS / 'app.ico'
        if icon.exists():
            root.iconbitmap(str(icon))
        compact = root.winfo_screenheight() < 900
        root.geometry('940x680' if compact else '1000x820')
        root.minsize(860, 660 if compact else 740)
        root.configure(bg='#F3F6F8')
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 10), foreground='#172B3A', background='#F3F6F8')
        style.configure('TFrame', background='#F3F6F8')
        style.configure('Card.TFrame', background='#FFFFFF')
        style.configure('TLabel', background='#FFFFFF', foreground='#172B3A')
        style.configure('Muted.TLabel', foreground='#687B8A')
        style.configure('Header.TLabel', background='#F3F6F8', font=('Segoe UI', 26, 'bold'))
        style.configure('Caption.TLabel', background='#F3F6F8', foreground='#687B8A')
        style.configure('Section.TLabel', font=('Segoe UI', 11, 'bold'))
        style.configure('TEntry', padding=9, fieldbackground='#FFFFFF', bordercolor='#D9E2E8')
        style.configure('TCombobox', padding=8, fieldbackground='#FFFFFF')
        style.map('TCombobox', fieldbackground=[('readonly', '#FFFFFF')])
        style.configure('TButton', padding=(14, 9), background='#EDF2F5', borderwidth=0)
        style.map('TButton', background=[('active', '#DFE8ED')], foreground=[('disabled', '#96A2AC')])
        style.configure('Accent.TButton', background='#137D78', foreground='#FFFFFF', font=('Segoe UI', 10, 'bold'))
        style.map('Accent.TButton', background=[('disabled', '#CEDADD'), ('active', '#086A65')], foreground=[('disabled', '#7A8D94')])
        style.configure('Horizontal.TProgressbar', background='#137D78', troughcolor='#E7EDF1', borderwidth=0, thickness=7)
        self.source = tk.StringVar(master=root)
        self.destination = tk.StringVar(master=root, value=self.settings.get('destination', str(Path.home() / 'Documents' / 'DimaScript')))
        language = self.settings.get('language', 'Русский')
        self.language = tk.StringVar(master=root, value=language if language in ('Русский', 'Автоопределение', 'English') else 'Русский')
        self.status = tk.StringVar(master=root, value='Готово к новой транскрипции')
        self.progress_text = tk.StringVar(master=root, value='Выберите файл и нажмите «Начать транскрипцию».')
        self.elapsed = tk.StringVar(master=root, value='')
        frame = ttk.Frame(root, padding=(20, 12) if compact else (28, 22))
        frame.pack(fill='both', expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(3, weight=1)
        header = ttk.Frame(frame)
        header.grid(row=0, column=0, sticky='ew', pady=(0, 10 if compact else 18))
        if (ASSETS / 'brand.png').is_file():
            self.brand_image = tk.PhotoImage(master=root, file=str(ASSETS / 'brand.png'))
            ttk.Label(header, image=self.brand_image, style='Caption.TLabel').pack(side='left', padx=(0, 14))
        heading = ttk.Frame(header)
        heading.pack(side='left')
        ttk.Label(heading, text='DimaScript', style='Header.TLabel').pack(anchor='w')
        ttk.Label(heading, text='Транскрипция аудио и видео', style='Caption.TLabel').pack(anchor='w', pady=(2, 0))
        setup = ttk.Frame(frame, style='Card.TFrame', padding=12 if compact else 20)
        setup.grid(row=1, column=0, sticky='ew')
        setup.columnconfigure(0, weight=1)
        ttk.Label(setup, text='01   Исходный файл', style='Section.TLabel').grid(row=0, column=0, sticky='w')
        self.source_entry = ttk.Entry(setup, textvariable=self.source)
        self.source_entry.grid(row=1, column=0, sticky='ew', pady=(8, 16))
        self.file_button = ttk.Button(setup, text='Выбрать файл…', command=self.choose_source)
        self.file_button.grid(row=1, column=1, padx=(12, 0), pady=(8, 16), sticky='ew')
        ttk.Label(setup, text='02   Сохранить результат', style='Section.TLabel').grid(row=2, column=0, sticky='w')
        self.dest_entry = ttk.Entry(setup, textvariable=self.destination)
        self.dest_entry.grid(row=3, column=0, sticky='ew', pady=(8, 4))
        self.folder_button = ttk.Button(setup, text='Выбрать папку…', command=self.choose_destination)
        self.folder_button.grid(row=3, column=1, padx=(12, 0), pady=(8, 4), sticky='ew')
        ttk.Label(setup, text='Для каждой записи — отдельная папка с текстом и субтитрами SRT.', style='Muted.TLabel').grid(row=4, column=0, columnspan=2, sticky='w', pady=(0, 14))
        controls = ttk.Frame(setup, style='Card.TFrame')
        controls.grid(row=5, column=0, columnspan=2, sticky='ew')
        controls.columnconfigure(1, weight=1)
        ttk.Label(controls, text='03   Язык записи', style='Section.TLabel').grid(row=0, column=0, sticky='w', pady=(0, 8))
        self.language_box = ttk.Combobox(controls, textvariable=self.language, values=['Русский', 'Автоопределение', 'English'], state='readonly', width=21)
        self.language_box.grid(row=1, column=0, sticky='w')
        self.start_button = ttk.Button(controls, text='Начать транскрипцию', style='Accent.TButton', command=self.start)
        self.start_button.grid(row=1, column=2, padx=(12, 8))
        self.stop_button = ttk.Button(controls, text='Остановить', command=self.stop, state='disabled')
        self.stop_button.grid(row=1, column=3)
        progress = ttk.Frame(frame, style='Card.TFrame', padding=12 if compact else 20)
        progress.grid(row=2, column=0, sticky='ew', pady=12)
        progress.columnconfigure(0, weight=1)
        ttk.Label(progress, textvariable=self.status, wraplength=790, style='Section.TLabel').grid(row=0, column=0, sticky='w')
        self.bar = ttk.Progressbar(progress, maximum=100)
        self.bar.grid(row=1, column=0, sticky='ew', pady=(13, 9))
        metrics = ttk.Frame(progress, style='Card.TFrame')
        metrics.grid(row=2, column=0, sticky='ew')
        metrics.columnconfigure(0, weight=1)
        ttk.Label(metrics, textvariable=self.progress_text, style='Muted.TLabel').grid(row=0, column=0, sticky='w')
        ttk.Label(metrics, textvariable=self.elapsed, style='Muted.TLabel').grid(row=0, column=1, sticky='e')
        result = ttk.Frame(frame, style='Card.TFrame', padding=12 if compact else 20)
        result.grid(row=3, column=0, sticky='nsew')
        result.columnconfigure(0, weight=1)
        result.rowconfigure(1, weight=1)
        ttk.Label(result, text='Текст записи', style='Section.TLabel').grid(row=0, column=0, sticky='w', pady=(0, 10))
        text_frame = ttk.Frame(result, style='Card.TFrame')
        text_frame.grid(row=1, column=0, sticky='nsew')
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        self.preview = tk.Text(text_frame, height=5, wrap='word', font=('Segoe UI', 11),
                               bg='#FFFFFF', fg='#172B3A', relief='flat', borderwidth=0,
                               padx=0, pady=5, spacing3=7, selectbackground='#CDE8E9', state='disabled')
        self.preview.grid(row=0, column=0, sticky='nsew')
        scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=self.preview.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.preview.configure(yscrollcommand=scrollbar.set)
        actions = ttk.Frame(result, style='Card.TFrame')
        actions.grid(row=2, column=0, sticky='ew', pady=(12, 0))
        self.copy_button = ttk.Button(actions, text='Копировать текст', command=self.copy_text, state='disabled')
        self.copy_button.pack(side='left')
        self.text_button = ttk.Button(actions, text='Открыть текст', command=self.open_text, state='disabled')
        self.text_button.pack(side='left', padx=8)
        self.open_button = ttk.Button(actions, text='Папка результата', command=self.open_output, state='disabled')
        self.open_button.pack(side='right')
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(150, self.poll)

    def save_settings(self):
        if self.test_mode:
            return
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.settings_path.with_suffix(f'.{os.getpid()}.tmp')
            self.settings = {
                'destination': self.destination.get(), 'language': self.language.get(),
                'source_directory': str(Path(self.source.get()).parent)
            }
            temporary.write_text(json.dumps(self.settings, ensure_ascii=False), encoding='utf-8')
            os.replace(temporary, self.settings_path)
        except OSError:
            pass

    def result_text(self):
        if self.output:
            for name in ('Транскрипция.txt', 'Транскрипция.partial.txt'):
                path = self.output / name
                if path.is_file():
                    return path
        return None

    def copy_text(self):
        path = self.result_text()
        if path:
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(path.read_text(encoding='utf-8-sig'))
            except Exception as error:
                from tkinter import messagebox
                messagebox.showerror('Не удалось скопировать текст', str(error))

    def open_text(self):
        path = self.result_text()
        if path:
            self.open_path(path)

    def open_path(self, path):
        try:
            os.startfile(str(path))
        except OSError as error:
            from tkinter import messagebox
            messagebox.showerror('Не удалось открыть', str(error))

    def choose_source(self):
        from tkinter import filedialog
        result = filedialog.askopenfilename(title='Выберите аудио или видео', initialdir=self.settings.get('source_directory', str(Path.home())),
                    filetypes=[('Видео и аудио', '*.mp4 *.mkv *.webm *.mov *.avi *.mp3 *.wav *.m4a *.flac *.ogg'), ('Все файлы', '*.*')])
        if result:
            self.source.set(result)

    def choose_destination(self):
        from tkinter import filedialog
        current = Path(self.destination.get().strip())
        result = filedialog.askdirectory(initialdir=str(current if current.is_dir() else Path.home()), title='Куда сохранить транскрипцию?')
        if result:
            self.destination.set(result)

    def set_busy(self, busy):
        for widget in [self.source_entry, self.dest_entry, self.file_button, self.folder_button, self.start_button]:
            widget.configure(state='disabled' if busy else 'normal')
        self.language_box.configure(state='disabled' if busy else 'readonly')
        self.stop_button.configure(state='normal' if busy else 'disabled')

    def start(self):
        from tkinter import messagebox
        if self.process is not None:
            return
        if not self.source.get().strip() or not self.destination.get().strip():
            messagebox.showerror('Проверьте пути', 'Укажите исходный файл и папку результата.')
            return
        source = Path(self.source.get().strip())
        destination = Path(self.destination.get().strip())
        if not source.is_file():
            messagebox.showerror('Файл не найден', 'Выберите существующий аудио- или видеофайл.')
            return
        try:
            destination.mkdir(parents=True, exist_ok=True)
            run_output = create_run_folder(destination, source.stem)
            language = {'Русский': 'ru', 'Автоопределение': 'auto', 'English': 'en'}[self.language.get()]
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['HF_HUB_OFFLINE'] = '1'
            event_path = run_output / 'Прогресс.jsonl'
            event_path.touch()
            env['TRANSCRIBER_EVENTS'] = str(event_path.resolve())
            command = [sys.executable] if getattr(sys, 'frozen', False) else [str(Path(sys.executable).with_name('python.exe')), str(Path(__file__).resolve())]
            self.log = (run_output / 'Диагностика.log').open('w', encoding='utf-8')
            self.process = subprocess.Popen(command + ['--worker',
                            str(source.resolve()), str(run_output.resolve()), language],
                            stdout=subprocess.DEVNULL, stderr=self.log, text=True, encoding='utf-8',
                            env=env, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except Exception as error:
            if hasattr(self, 'log'):
                self.log.close()
            messagebox.showerror('Не удалось запустить', str(error))
            return
        self.output = run_output
        self.save_settings()
        self.completed = self.cancelled = False
        self.started = time.monotonic()
        self.set_busy(True)
        self.open_button.configure(state='normal')
        self.copy_button.configure(state='disabled')
        self.text_button.configure(state='disabled')
        self.preview.configure(state='normal')
        self.preview.delete('1.0', 'end')
        self.preview.configure(state='disabled')
        self.bar.configure(mode='indeterminate')
        self.bar['value'] = 0
        self.bar.start(15)
        self.stage = 'Подготовка…'
        self.status.set(self.stage)
        process = self.process
        def read_events():
            with event_path.open(encoding='utf-8') as events:
                while True:
                    position = events.tell()
                    line = events.readline()
                    if line.endswith('\n'):
                        try:
                            self.events.put(json.loads(line))
                        except ValueError:
                            pass
                    elif process.poll() is not None:
                        break
                    else:
                        events.seek(position)
                        time.sleep(0.1)
            self.events.put({'kind': 'exit', 'code': process.wait()})
        threading.Thread(target=read_events, daemon=True).start()

    def poll(self):
        while not self.events.empty():
            event = self.events.get_nowait()
            kind = event['kind']
            if kind == 'stage':
                self.stage = event['text']
                self.status.set(self.stage)
            elif kind == 'progress':
                self.bar.stop()
                self.bar.configure(mode='determinate')
                duration = event['duration']
                percent = min(99, event['position'] / duration * 100) if duration else 0
                self.bar['value'] = percent
                self.stage = 'Распознавание речи…'
                self.status.set(self.stage)
                self.progress_text.set(f'{percent:.0f}% · {timestamp(event["position"])[:8]} / {timestamp(duration)[:8]} записи')
                if event['position'] and event['text']:
                    self.preview.configure(state='normal')
                    self.preview.insert('end', event['text'] + '\n')
                    self.preview.see('end')
                    self.preview.configure(state='disabled')
            elif kind == 'done':
                self.completed = True
                self.bar.stop()
                self.bar.configure(mode='determinate')
                self.bar['value'] = 100
                self.status.set('Транскрипция завершена' if event['count'] else 'Речь не обнаружена')
                self.progress_text.set('100% · Текст и субтитры сохранены' if event['count'] else '100% · Проверьте звук и выбранный язык')
            elif kind == 'exit':
                self.bar.stop()
                if str(self.bar['mode']) == 'indeterminate':
                    self.bar.configure(mode='determinate', value=0)
                if self.completed:
                    self.bar['value'] = 100
                self.log.close()
                self.process = None
                self.set_busy(False)
                if self.result_text():
                    self.copy_button.configure(state='normal')
                    self.text_button.configure(state='normal')
                if not self.completed:
                    has_partial = self.result_text() is not None
                    self.status.set('Транскрипция остановлена' if self.cancelled else 'Не удалось завершить транскрипцию')
                    self.progress_text.set(('Частичный текст сохранён' if has_partial else 'Распознавание не успело начаться') if self.cancelled else 'Подробности: Диагностика.log в папке результата')
        if self.process and self.started is not None:
            self.elapsed.set('Прошло ' + timestamp(time.monotonic() - self.started)[:8])
            if str(self.bar['mode']) == 'indeterminate':
                self.progress_text.set('Подготовка записи · процент появится после чтения аудио')
        self.root.after(150, self.poll)

    def stop(self):
        if self.process and self.process.poll() is None:
            self.cancelled = True
            self.process.terminate()
            self.stop_button.configure(state='disabled')
            self.status.set('Остановка…')

    def open_output(self):
        if self.output and self.output.is_dir():
            self.open_path(self.output)

    def close(self):
        from tkinter import messagebox
        if self.process and self.process.poll() is None:
            if not messagebox.askyesno('Остановить распознавание?', 'Обработка ещё идёт. Закрыть приложение и сохранить неполный результат?'):
                return
            self.process.terminate()
            self.process.wait()
        self.root.destroy()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--worker':
        if os.environ.get('TRANSCRIBER_EVENTS'):
            sys.stdout = open(os.environ['TRANSCRIBER_EVENTS'], 'a', encoding='utf-8', buffering=1)
        if sys.stderr is None:
            sys.stderr = open(Path(sys.argv[3]) / 'Диагностика.log', 'a', encoding='utf-8')
        try:
            worker(*sys.argv[2:5])
        except Exception:
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        import tkinter as tk
        from tkinter import ttk
        root = tk.Tk()
        ttk.Style().theme_use('clam')
        app = App(root, test_mode='--self-test' in sys.argv or '--preview' in sys.argv)
        if len(sys.argv) > 1 and sys.argv[1] == '--self-test':
            root.withdraw()
            app.source.set(sys.argv[2])
            app.destination.set(sys.argv[3])
            app.start()
            deadline = time.monotonic() + 90
            def check_test():
                if app.process is not None and time.monotonic() < deadline:
                    root.after(100, check_test)
                    return
                result = {'completed': app.completed, 'progress': float(app.bar['value']),
                          'status': app.status.get(), 'output': str(app.output),
                          'model_cache': str(MODEL_CACHE)}
                (Path(sys.argv[3]) / 'gui-test.json').write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
                if app.process is not None:
                    app.stop()
                root.destroy()
            root.after(100, check_test)
        root.mainloop()
