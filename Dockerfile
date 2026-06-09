# Stage 1: Build the React frontend
FROM node:18-alpine AS frontend-build
WORKDIR /app/client
COPY client/package*.json ./
RUN npm install
COPY client/ ./
RUN npm run build

# Stage 2: Build the Python backend and serve
FROM python:3.10-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Force CPU version of PyTorch to keep image small
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Copy the entire app
COPY . .

# Copy the built React app from the frontend stage
COPY --from=frontend-build /app/client/dist ./client/dist

# Expose the port used by Hugging Face Spaces
EXPOSE 7860

# Ensure start script is executable
RUN chmod +x deploy/start.sh

CMD ["./deploy/start.sh"]
