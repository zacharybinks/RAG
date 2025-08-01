# File: ./rfp-rag-frontend/Dockerfile (Corrected)

# --- STAGE 1: Build the React App ---
FROM node:18 as builder
WORKDIR /app

# **FIX**: Copy package files first in a separate, explicit step.
COPY package.json ./
COPY package-lock.json ./

# Use 'npm ci' for a clean, reliable install from the lock file.
RUN npm ci

# Copy the rest of the application source code, including nginx.conf
COPY . .

# Set the production API URL during the build
ARG REACT_APP_API_URL
ENV REACT_APP_API_URL=$REACT_APP_API_URL

# Run the production build
RUN npm run build

# --- STAGE 2: Serve with Nginx ---
FROM nginx:stable-alpine
# Copy the built assets from the 'builder' stage
COPY --from=builder /app/build /usr/share/nginx/html
# Copy the Nginx configuration from the build context
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
