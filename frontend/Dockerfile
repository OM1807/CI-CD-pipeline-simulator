FROM node:20-alpine

WORKDIR /app

COPY package.json ./
RUN npm install --legacy-peer-deps

COPY . .

# Run Vite in host mode
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
