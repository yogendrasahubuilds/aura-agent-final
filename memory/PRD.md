# AURA — Autonomous Universal Resource Agent

## Problem Statement
AI-agent web app that converts natural-language goals into multi-step booking workflows for movies, hotels, and flights. All bookings are SIMULATED/DEMO for a college viva project.

## Stack
- Frontend: React + Tailwind + shadcn/ui (user chose React over vanilla JS for the pre-configured deploy pipeline)
- Backend: FastAPI + MongoDB (Motor)
- Agent: Emergent LLM key (OpenAI gpt-5.4-mini) with regex fallback

## Core Requirements
1. Natural-language parsing → intent + params
2. Mock search for movies / hotels / flights (realistic Indian cities, INR prices)
3. Price calculation (18% GST)
4. User confirmation required before booking
5. Mock booking creation + verification
6. Execution timeline (8 steps) visualization
7. Booking history

## Users
- B.Tech students demoing an AI-agent workflow during viva
- Judges / examiners wanting to see end-to-end agent reasoning

## Implementation Status (2026-02)
- [x] Backend: /api/chat, /api/search, /api/confirm, /api/book, /api/booking/{id}, /api/bookings, /api/meta
- [x] Agent (agent.py): LLM-primary + regex-fallback parsing of 3 intents with date/city/count extraction
- [x] Tools (tools.py): movie_search, hotel_search, flight_search, calculator with tool registry (risk-tagged)
- [x] Booking (booking.py): AURA-MOV/HOT/FLT ID generation + verification
- [x] Mock datasets (data.py): 10 movies, 10 hotels, 10 flights across Bhilai/Raipur/Delhi/Mumbai/Bengaluru
- [x] Frontend: AuraApp page with chat input, 3 preset chips, timeline sidebar, parameters card, options list, confirmation, receipt, history tab
- [x] Testing agent: 100% pass on both backend and frontend
- [x] Hotel pricing fix: subtotal = price × nights (guests no longer multiply)

## Backlog (future ideas)
- P1: Seat/row picker for movies, room-type selector for hotels, return-flight for round-trips
- P1: Downloadable PDF ticket (jsPDF)
- P2: Dark-mode toggle
- P2: Multi-city flight search
- P2: WebSocket streaming of agent "thinking" steps
- P2: Admin panel to add more mock data
