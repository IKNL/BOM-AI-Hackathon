FROM node:18-alpine

# Install pnpm
RUN corepack enable && corepack prepare pnpm@9 --activate

WORKDIR /app

# Copy dependency files first for layer caching
COPY package.json pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy application source
COPY . .

# Set backend URL for Next.js rewrites (baked at build time)
ARG BACKEND_URL=http://backend:8000
ENV BACKEND_URL=${BACKEND_URL}

# Build the Next.js application
RUN pnpm build

# Expose port
EXPOSE 3000

# Run the production server
CMD ["pnpm", "start"]
