# 🎨 KalaKarigar.ai

*Empowering Indian Artisans with AI-Powered Marketing Tools*

[![Made with Streamlit](https://img.shields.io/badge/Made%20with-Streamlit-FF4B4B)](https://streamlit.io/)
[![Google Cloud](https://img.shields.io/badge/Powered%20by-Google%20Cloud-4285F4)](https://cloud.google.com/)
[![Firebase](https://img.shields.io/badge/Database-Firebase-FFA611)](https://firebase.google.com/)
[![Gemini AI](https://img.shields.io/badge/AI-Gemini%202.5%20Flash-blue)](https://ai.google.dev/)

---

### 🚀 Project Demo

[🎬 Watch Demo Video (Google Drive)](https://drive.google.com/file/d/1wCaeXdyJIYKxJvwTIy6tBZJUmT28RCa_/view?usp=sharing)


---
## 🌟 Vision

**KalaKarigar.ai** is a comprehensive AI-powered platform designed to bridge the digital divide for Indian artisans. By leveraging cutting-edge generative AI technologies, we enable craftspeople to create professional marketing content, enhance product imagery, and build a strong digital presence without requiring technical expertise.

---

## ✨ Complete Feature Set

### 📝 **Step 1: Product Details & Voice Input**
- **Multi-language Voice Recording**: Support for English, Hindi, and Gujarati
- **AI Transcription**: Google Cloud Speech-to-Text with automatic language detection
- **Smart Translation**: Seamless translation to English for global reach
- **AI Tag Generation**: Google Cloud Vision AI analyzes product images for automatic tagging
- **Product Information Capture**: Craft type, materials, dimensions, and detailed descriptions

### 🤖 **Step 2: AI Content Generation**
- **Enhanced Product Descriptions**: Gemini 2.5 Flash creates compelling, professional descriptions
- **Social Media Captions**: Multiple ready-to-use captions optimized for different platforms
- **Trending Hashtags**: AI-generated hashtags incorporating product analysis and trends
- **Multi-format Output**: Content optimized for Instagram, Facebook, WhatsApp Business

### 🎨 **Step 3: AI Image Enhancement**
- **Vibrant Style**: Enhanced colors and contrast for eye-catching appeal
- **Studio Style**: Professional studio lighting with clean backgrounds
- **Festive Style**: Warm, celebratory atmosphere for cultural products
- **Fallback Processing**: PIL-based enhancement when AI services are unavailable
- **Image Optimization**: Automatic resizing and quality optimization

### ☁️ **Step 4: Google Drive Integration**
- **One-Click Export**: Complete marketing pack exported to organized Google Drive folders
- **Structured Organization**: Automatic folder creation with timestamps and metadata
- **Multiple File Formats**: Enhanced images (PNG) and marketing content (TXT)
- **Easy Sharing**: Direct Google Drive links for instant access and sharing

### 🔐 **Authentication & Security**
- **Google OAuth Integration**: Secure login with Google accounts
- **Session Persistence**: Users stay logged in across browser sessions
- **User Profile Management**: Automatic user information retrieval
- **Secure Credential Handling**: Industry-standard OAuth 2.0 implementation

---

## 🎯 User Journey

![Process Flow Diagram](assets/Process%20flow%20diagram.png)

1. **🔐 Secure Login**: Google OAuth authentication with persistent sessions
2. **📝 Product Input**: Voice recording in native language or text input
3. **🤖 AI Processing**: Automatic transcription, translation, and content generation
4. **🎨 Image Enhancement**: Choose from AI-powered styling options
5. **☁️ Export**: One-click export to organized Google Drive folders
6. **📱 Share**: Ready-to-use content for all social media platforms

---

## 🏗️ Advanced Tech Stack

### **Frontend & UI**
- **Streamlit**: Modern web application framework with custom CSS theming
- **Responsive Design**: Mobile-friendly interface with adaptive layouts
- **Progressive Enhancement**: Works across all devices and screen sizes

### **AI & Machine Learning**
- **Gemini 2.5 Flash**: Advanced text and image generation
- **Google Cloud Speech-to-Text**: Multi-language voice transcription
- **Google Cloud Translation**: Seamless language translation
- **Google Cloud Vision AI**: Intelligent image analysis and tagging

### **Backend & Storage**
- **Firebase Admin SDK**: Scalable NoSQL database for artisan data
- **Firebase Storage**: Secure cloud storage for product images
- **Google Drive API**: Seamless integration for content export

### **Audio Processing**
- **Streamlit AudioRec**: Real-time voice recording
- **Pydub**: Audio format conversion and optimization
- **FFmpeg**: Advanced audio processing capabilities

### **Image Processing**
- **Pillow (PIL)**: Comprehensive image manipulation
- **Advanced Optimization**: Multiple quality settings and format support
- **Fallback Systems**: Reliable image processing when AI is unavailable

---

## 📂 Project Architecture

![System Architecture Diagram](assets/Architecture%20diagram.png)

```
KalaKarigar.ai/
├── app.py                          # Main Streamlit application with UI/UX
├── requirements.txt                # Python dependencies
├── .streamlit/
│   └── secrets.toml               # Configuration secrets
├── utils/
│   ├── ai_utils.py                # Gemini AI integration with caching
│   ├── firebase_utils.py          # Firebase operations with retry logic
│   ├── gcp_ai_utils.py           # Google Cloud AI services
│   ├── gdrive_utils.py           # Google Drive integration
│   └── image_utils.py            # Image enhancement with fallback
├── assets/
│   ├── logo_desktop.png          # Desktop logo
│   ├── logo_mobile.png           # Mobile responsive logo
│   └── favicon.png               # Application favicon
└── README.md                     # This file
```

---

## ⚡ Quick Start Guide

### 1. **Clone the Repository**

```bash
git clone https://github.com/Yash-Kakadiya/KalaKarigar.ai.git
cd KalaKarigar.ai
```

### 2. **Install Dependencies**

```bash
pip install -r requirements.txt
```

### 3. **Configure Secrets**

Create `.streamlit/secrets.toml` with the following structure:

```toml
# Gemini AI API Key
GEMINI_API_KEY = "your_gemini_api_key"

# Firebase Configuration
[firebase_credentials]
type = "service_account"
project_id = "your_project_id"
private_key_id = "your_private_key_id"
private_key = "your_private_key"
client_email = "your_client_email"
client_id = "your_client_id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "your_cert_url"

# Google Cloud Platform Service Account
[gcp_service_account]
type = "service_account"
project_id = "your_project_id"
private_key_id = "your_private_key_id"
private_key = "your_private_key"
client_email = "your_client_email"
client_id = "your_client_id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "your_cert_url"

# Google Drive OAuth Credentials
[gdrive_oauth_credentials]
client_id = "your_oauth_client_id"
client_secret = "your_oauth_client_secret"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
redirect_uris = ["your_redirect_uri"]
```

### 4. **Required Google Cloud APIs**

Enable the following APIs in your Google Cloud Console:
- **Gemini AI API** (or Vertex AI API)
- **Cloud Speech-to-Text API**
- **Cloud Translation API**
- **Cloud Vision API**
- **Google Drive API**
- **People API**

### 5. **Firebase Setup**

1. Create a new Firebase project
2. Enable Firestore Database
3. Enable Firebase Storage
4. Generate service account credentials
5. Add credentials to `secrets.toml`

### 6. **Run Locally**

```bash
streamlit run app.py
```

---

## 🚀 Deployment Options

### **Streamlit Cloud** (Recommended)
1. Fork the repository
2. Connect to Streamlit Cloud
3. Add secrets through the Streamlit Cloud interface
4. Deploy with one click

### **Google Cloud Run**
```bash
# Build and deploy
gcloud run deploy kalakarigar-ai \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### **Local Docker**
```bash
# Build Docker image
docker build -t kalakarigar-ai .

# Run container
docker run -p 8501:8501 kalakarigar-ai
```

---


## 📊 API Usage & Limits

- **Gemini AI**: Rate limited per project quota
- **Google Cloud Speech**: 60 minutes/month free tier
- **Google Cloud Vision**: 1,000 requests/month free tier
- **Google Cloud Translation**: 500,000 characters/month free tier
- **Firebase**: Generous free tier with pay-as-you-grow pricing

---

## 🤝 Contributing

We welcome contributions from the community! Please read our contributing guidelines and submit pull requests for any improvements.

### **Development Setup**
1. Fork the repository
2. Create a feature branch
3. Make your changes with proper testing
4. Submit a pull request with detailed description

---


## 👨‍💻 Creator

**Yash Kakadiya**
- 🌐 GitHub: [@Yash-Kakadiya](https://github.com/Yash-Kakadiya)
- 💼 LinkedIn: [Yash Kakadiya](https://linkedin.com/in/yash-kakadiya-)
- 📧 Email: kakadiyayash77@gmail.com

---

## 🙏 Acknowledgments

- **Google Cloud Platform** for providing robust AI and cloud services
- **Streamlit** for the excellent web app framework
- **Firebase** for scalable backend infrastructure


---

<div align="center">

**Made with ❤️ for Indian Artisans**

*Preserving Traditional Crafts in the Digital Age*

</div>