# --- STAGE 1: Build the React App ---
FROM node:18 as builder
WORKDIR /app
COPY package.json yarn.lock ./
RUN yarn install
COPY . .
# Set the production API URL during the build
ARG REACT_APP_API_URL
ENV REACT_APP_API_URL=$REACT_APP_API_URL
RUN yarn build

# --- STAGE 2: Serve with Nginx ---
FROM nginx:stable-alpine
COPY --from=builder /app/build /usr/share/nginx/html
# Copy the custom Nginx configuration
COPY ../nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]