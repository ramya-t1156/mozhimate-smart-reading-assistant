# மொழிMate (MozhiMate)

MozhiMate is a Flask + MongoDB reading assistant that combines NLP, CV, OCR, speech-ready processing, revision logic, streak tracking, and a lightweight deep-learning-inspired difficulty scoring flow.

## Setup

1. Create a virtual environment and install dependencies from `requirements.txt`.
2. Start MongoDB locally and set `MONGO_URI` if needed.
3. Run the app with `python app.py`.

## Environment Variables

- `SECRET_KEY`
- `MONGO_URI`

## Notes

- `Image Mode` requires OpenCV and Tesseract OCR installed on the machine.
- `PDF Mode` requires PyMuPDF.
- `Pronunciation` uses `pyttsx3` and may depend on local audio support.
- `Speech Mode` is wired for transcript processing in the web UI; browser microphone capture can be layered onto it next if needed.
