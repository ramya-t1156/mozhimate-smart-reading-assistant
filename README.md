# MozhiMate – Smart Real-Time Reading Assistant

MozhiMate is a web-based reading assistant built using Python, Flask, and MongoDB. It combines Natural Language Processing (NLP), Computer Vision (CV), OCR, and vocabulary revision features to help users understand unfamiliar words while reading.

## Why This Project?

While reading books, articles, or documents, learners often come across unfamiliar words and need to interrupt their reading to search for meanings. MozhiMate aims to make vocabulary learning easier by providing word meanings, pronunciation, and revision features in one place.

## Features

- Multiple input modes: Text, Speech, Image, and PDF
- Word meanings, synonyms, and examples
- Word pronunciation support
- Vocabulary revision and quizzes
- Daily learning streak tracking
- Learning analytics dashboard
- Word difficulty scoring

## Screenshots

### Home Page

<img width="475" height="392" alt="image" src="https://github.com/user-attachments/assets/a5029707-0250-40ba-916a-d2824c15d060" />

### Speech Mode Page

<img width="482" height="234" alt="image" src="https://github.com/user-attachments/assets/e82004f4-095d-4c0f-9d3b-b2325c122172" />

### Quiz Mode page

<img width="482" height="321" alt="image" src="https://github.com/user-attachments/assets/acafab4c-093d-473f-8bd3-02cb1b4bc3dc" />


## Technologies Used

- **Backend:** Python, Flask
- **Frontend:** HTML, CSS, JavaScript
- **Database:** MongoDB
- **NLP:** NLTK, WordNet
- **Computer Vision and OCR:** OpenCV, Tesseract OCR
- **Deep Learning:** TensorFlow 

## Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/ramya-t1156/mozhimate-smart-reading-assistant.git
   ```

2. Navigate to the project folder:

   ```bash
   cd mozhimate-smart-reading-assistant
   ```

3. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   ```

   On Windows:

   ```bash
   venv\Scripts\activate
   ```

4. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Start MongoDB and configure the required environment variables.

6. Run the application:

   ```bash
   python app.py
   ```

## Environment Variables

Configure the following environment variables if required:

- `SECRET_KEY`
- `MONGO_URI`

## Notes

- Image Mode requires OpenCV and Tesseract OCR.
- PDF Mode requires PyMuPDF.
- Pronunciation uses `pyttsx3` and may require local audio support.
- Speech Mode depends on the speech-processing functionality currently implemented in the application.

## Contact

- **Email:** ramyathangamuthu7783@gmail.com
- **GitHub:** [ramya-t1156](https://github.com/ramya-t1156)
