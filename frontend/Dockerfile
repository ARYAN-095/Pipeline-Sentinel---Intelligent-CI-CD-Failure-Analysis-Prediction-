# frontend/Dockerfile

# 1. Base Image: Use an official Node.js image
FROM node:18-alpine

# 2. Set Working Directory
WORKDIR /app

# 3. Copy package.json and install dependencies
COPY package*.json ./
RUN npm install

# 4. Copy the rest of the application code
COPY . .

# 5. Build the Next.js application
RUN npm run build

# 6. Expose the port the app runs on
EXPOSE 3000

# 7. Command to run the application
CMD ["npm", "start"]
