# 🤖 TalentScout – AI Interview Assistant

TalentScout is an **intelligent hiring assistant chatbot** designed to streamline the initial screening of candidates. It gathers essential candidate information, evaluates technical knowledge based on the declared tech stack, and records performance for recruiters.

The system is built with **Streamlit + LangChain + Hugging Face models**, making the recruitment process smarter and more efficient.

---

## 📌 Features

✅ Collects candidate’s basic details (Name, Contact Info, Desired Role, Experience, Tech Stack)
✅ Asks **tech-specific interview questions** dynamically
✅ Stores candidate details in `candidates.csv`
✅ Records candidate responses with **auto-scored evaluation** in `performance.csv`
✅ User-friendly **Streamlit web interface**
✅ Built-in support for **LangChain + Hugging Face models**
✅ Easily extensible to other tech stacks

---

## 🖼️ Project Demo

### 🔹 Landing Page

<img width="1853" height="1042" alt="Screenshot from 2025-08-28 17-08-21" src="https://github.com/user-attachments/assets/9e18ce42-6803-4be8-bf58-fa396ecd568a" />


### 🔹 Candidate Details Form

<img width="1853" height="1042" alt="Screenshot from 2025-08-28 17-16-30" src="https://github.com/user-attachments/assets/dead83c4-617e-42d4-bb7c-597daaa02554" />

### 🔹 Interview Process

<img width="1853" height="1042" alt="Screenshot from 2025-08-28 17-17-28" src="https://github.com/user-attachments/assets/cdead0de-6fa0-41ba-960a-db0520227474" />

<img width="1853" height="1042" alt="Screenshot from 2025-08-28 17-21-08" src="https://github.com/user-attachments/assets/b99b65d5-0ac5-4469-9f40-18448d054b0c" />

### 🔹 Performance Evaluation

<img width="1853" height="1042" alt="Screenshot from 2025-08-28 17-21-23" src="https://github.com/user-attachments/assets/a492d00b-fdbf-413b-9891-dd453b077313" />

<img width="1853" height="1042" alt="Screenshot from 2025-08-28 17-21-37" src="https://github.com/user-attachments/assets/bdd5d8ad-a19b-4178-8160-0cae9a4efeb4" />

---

## 🛠️ Tech Stack

* **Frontend & UI:** [Streamlit](https://streamlit.io/)
* **AI & NLP:** [LangChain](https://www.langchain.com/), Hugging Face Transformers
* **Data Storage:** CSV (`candidates.csv`, `performance.csv`)
* **Deployment:** Local (Streamlit)

---

## ⚙️ Installation

1. Clone this repository

   ```bash
   git clone https://github.com/AbhishekDongre14/AI_Interviewer.git
   cd AI_Interviewer.git
   ```

2. Create & activate a virtual environment

   ```bash
   python -m venv venv
   source venv/bin/activate   # For Linux/Mac
   venv\Scripts\activate      # For Windows
   ```

3. Install dependencies

   ```bash
   pip install -r requirements.txt
   ```

---

## 🔑 Environment Variables

Create a `.env` file in the **core/** folder and add the following:

```env
LANGCHAIN_TRACING_V2=true
HUGGINGFACEHUB_API_TOKEN=YOUR_HUGGINGFACEHUB_API_TOKEN
LANGCHAIN_ENDPOINT=YOUR_LANGCHAIN_ENDPOINT
LANGCHAIN_API_KEY=YOUR_LANGCHAIN_API_KEY
```

> ⚠️ Replace the placeholders with your actual API keys.

---

## 🚀 Running the App

Start the Streamlit app:

```bash
streamlit run app.py
```

Open your browser and visit:

```
http://localhost:8501
```

---

## 📂 Data Storage

* `data/candidates.csv` → Stores candidate basic information
<img width="1853" height="1042" alt="Screenshot from 2025-08-28 17-21-59" src="https://github.com/user-attachments/assets/3af209b1-fd27-431d-9a8a-c40f7821cff7" />

* `data/performance.csv` → Stores candidate responses with scores
<img width="1853" height="1042" alt="Screenshot from 2025-08-28 17-22-10" src="https://github.com/user-attachments/assets/f0a0ee86-c961-4e1f-9bfd-348d4e8a6320" />

---

## 📌 Future Enhancements

* 🔹 Add support for **multi-round interviews**
* 🔹 Export results in **PDF format** for recruiters
* 🔹 Integration with **ATS (Applicant Tracking Systems)**
* 🔹 Add **Docker deployment support**

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature-name`)
3. Commit your changes (`git commit -m 'Add new feature'`)
4. Push to the branch (`git push origin feature-name`)
5. Open a Pull Request

---

## 📜 License

This project is licensed under the **MIT License* – feel free to use, modify, and distribute.

---
