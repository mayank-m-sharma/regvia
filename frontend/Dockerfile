FROM node:20-alpine
WORKDIR /app
RUN npm install -g pnpm@10.34.4
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
EXPOSE 5173
CMD ["pnpm", "dev"]
