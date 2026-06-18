# syntax=docker/dockerfile:1

# --- Stage 1: build the SPA ---
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Vite bakes VITE_* env at build time. The browser reaches the API via the nginx
# proxy at /api on the same origin (see nginx.conf), so no API host is hardcoded.
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# --- Stage 2: serve static files + reverse-proxy /api to the api service ---
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
