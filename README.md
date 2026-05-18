# Arogya Virohan — Posture Analysis Platform

## Overview

A full-stack posture analysis platform built using:

* Next.js + TypeScript frontend
* FastAPI backend
* MediaPipe pose estimation
* Biomechanical posture calculations
* Clinical report generation pipeline

The platform allows users to:

1. Upload posture images
2. Detect body landmarks using MediaPipe
3. Calculate posture deviations
4. Classify severity levels
5. Generate a structured clinical posture report

---

# Features

## Frontend

* Multi-step posture assessment workflow
* Upload and preview posture images
* Reusable report component architecture
* Severity-based visualization system
* Dynamic report rendering from backend API
* Export-ready clinical report layout
* Fully typed TypeScript models

## Backend

* FastAPI posture analysis endpoint
* MediaPipe-based landmark detection
* Geometric posture calculations
* Severity classification pipeline
* Clinical synthesis generator
* Structured report response builder
* Modular posture-analysis architecture

---

# Tech Stack

## Frontend

* Next.js 16
* TypeScript
* TailwindCSS
* React

## Backend

* FastAPI
* MediaPipe
* OpenCV
* NumPy
* Python

---

# Architecture

```text
Frontend (Next.js)
        ↓
FastAPI Backend
        ↓
MediaPipe Pose Detection
        ↓
Landmark Extraction
        ↓
Biomechanical Calculations
        ↓
Severity Classification
        ↓
Clinical Synthesis
        ↓
Structured Report Generation
```

---

# Project Structure

```text
av-suite/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   └── services/posture/
│   └── tests/
│
└── frontend/
    └── posture-tool/
        ├── src/components/
        ├── src/lib/
        ├── src/types/
        └── src/data/
```

---

# Backend Pipeline

## Detection

MediaPipe detects:

* Head
* Shoulders
* Spine
* Pelvis
* Knee landmarks

## Calculations

Implemented posture metrics:

* Craniovertebral Angle (CVA)
* Shoulder Asymmetry
* Pelvic Obliquity
* Forward Trunk Lean

## Classification

Metrics are classified into:

* None
* Mild
* Moderate
* Severe

---

# API Endpoint

## Analyze Posture

```http
POST /posture/analyze
```

### Request

Multipart image upload:

```text
side_image=<image file>
```

### Response

Returns:

* Patient metadata
* Side/front/back posture views
* Measurements
* Severity levels
* Clinical synthesis
* Global posture index

---

# Setup Instructions

## Clone Repository

```bash
git clone https://github.com/Aarogya-Virohan/av-suite.git
cd av-suite
```

---

# Frontend Setup

```bash
cd frontend/posture-tool
npm install
npm run dev
```

Frontend runs on:

```text
http://localhost:3000
```

---

# Backend Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend runs on:

```text
http://127.0.0.1:8000
```

Swagger docs:

```text
http://127.0.0.1:8000/docs
```

---

# Testing

## Frontend Production Build

```bash
npm run build
```

## Backend Tests

```bash
pytest
```

---

# Future Improvements

* Multi-view posture fusion
* PDF clinical report export
* ML-based posture classification
* Exercise recommendation engine
* Historical posture tracking
* Authentication and patient records
* Real-time webcam posture analysis

---

# Screenshots

Add screenshots here:

* Upload screen
* Analysis screen
* Final report screen

---

# Author

Developed as part of the Arogya Virohan posture analysis initiative.
