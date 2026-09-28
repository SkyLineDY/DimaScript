# Third-party components

The MIT license in this repository covers DimaScript's original application code and artwork. It does not replace the licenses of the following components.

## Speech recognition

| Component | Version / revision | License | Source |
|---|---|---|---|
| OpenAI Whisper | small model | MIT | https://github.com/openai/whisper |
| SYSTRAN converted Whisper small | `536b0662742c02347bc0e980a01041f333bce120` | MIT | https://huggingface.co/Systran/faster-whisper-small |
| faster-whisper | 1.2.1 | MIT | https://github.com/SYSTRAN/faster-whisper/tree/v1.2.1 |
| CTranslate2 | 4.8.2 | MIT; bundled libraries have separate terms | https://github.com/OpenNMT/CTranslate2/tree/v4.8.2 |
| Tokenizers | 0.23.2 | Apache-2.0 | https://github.com/huggingface/tokenizers |
| ONNX Runtime | 1.30.0 | MIT and third-party notices | https://github.com/microsoft/onnxruntime |

Whisper copyright: Copyright (c) 2022 OpenAI. Faster-whisper copyright: Copyright (c) 2023 SYSTRAN. Full notices are included in `licenses/whisper` and `licenses/faster-whisper`.

## Media decoding

PyAV 18.1.0 is BSD-3-Clause. Its Windows media-library bundle includes FFmpeg 8.1.2, x264, x265, LAME, libiconv and other codec libraries. Some of these components are licensed under GPL-3.0-or-later or LGPL, rather than MIT. Do not treat the Windows distribution as an MIT-only bundle.

The matching PyAV/FFmpeg build recipe, patches, component source archives and GPL/LGPL license texts are provided in the release's `DimaScript-Media-Sources.zip`. The recipe is pinned to [pyav-ffmpeg 8.1.2-1](https://github.com/PyAV-Org/pyav-ffmpeg/tree/8.1.2-1). Component copyright notices remain in the included source archives and license directory.

You may modify or replace the media libraries under their respective licenses. DimaScript imposes no additional restriction on exercising rights granted by those licenses. Redistribution of GPL/LGPL components must retain the applicable notices and provide corresponding source under the relevant license terms.

## Runtime and other dependencies

Python is distributed under the PSF license and notices included in `licenses/Python`. Tcl/Tk use their included license terms. NumPy includes its own license bundle and OpenBLAS notices. Certifi uses MPL-2.0. Intel's OpenMP runtime retains Intel's redistribution terms; Microsoft runtime libraries retain Microsoft's terms. Unused NVIDIA cuDNN libraries are not included in this CPU distribution.

The remaining pinned Python dependencies and their verbatim license notices are listed in `requirements-build.txt` and `licenses/`. Source archives are available in the release's `DimaScript-Python-Sources.zip`. PyInstaller's bootloader is covered by its GPL exception; see `licenses/pyinstaller`.

Neither these acknowledgements nor the use of these components implies endorsement by their authors.
