# backend/Dockerfile

# 1. Base Image: Use an official Node.js image
FROM node:18-alpine

# 2. Set Working Directory
WORKDIR /app

# 3. Copy package.json and install dependencies
COPY package*.json ./
RUN npm install

# 4. Copy the rest of the application code
COPY . .

# 5. Expose the port the app runs on
EXPOSE 3001

# 6. Command to run the application
CMD ["node", "index.js"]
