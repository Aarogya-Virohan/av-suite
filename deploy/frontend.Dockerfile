FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency specifications first for optimal layer caching
COPY frontend/crm/package.json frontend/crm/package-lock.json ./
RUN npm ci

# Copy application source and workspace packages
COPY frontend/crm ./
COPY packages ../../packages

# Build arguments for Next.js public environment variables
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL:-/api/v1}
ENV NODE_ENV=production

RUN npm run build

# Production Runner Stage
FROM node:20-alpine AS runner

WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000

# Run as non-root user for security
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/package-lock.json ./package-lock.json
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000

CMD ["npm", "run", "start"]
