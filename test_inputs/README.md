# Real-world inference inputs

Place user-provided media in these folders; do not use placeholder names.

- Images: `test_inputs/images/` (`.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp`)
- Videos: `test_inputs/videos/` (`.mp4`, `.avi`, `.mov`, `.mkv`, `.webm`)

Run image inference from the project root:

```powershell
Get-ChildItem .\test_inputs\images -File
.\.venv\Scripts\python.exe tests\test_video_input.py .\test_inputs\images\actual-file.jpg --output .\runs\inference
```

Run video inference:

```powershell
Get-ChildItem .\test_inputs\videos -File
.\.venv\Scripts\python.exe tests\test_video_input.py .\test_inputs\videos\actual-file.mp4 --output .\runs\inference
```

Record one row per reviewed image or representative video frame in `reports/failure_analysis.csv`.
`expected_detection` is the manually verified ground truth; `actual_detection` and `confidence` come from the annotated output and terminal log. Use `false_positive`, `false_negative`, or `correct` for `error_type`.
