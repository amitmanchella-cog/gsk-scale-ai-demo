# Builds both packages and serves them with the Rsbuild preview servers.
FROM node:22-slim
WORKDIR /app
COPY package.json package-lock.json federation.shared.ts tsconfig.base.json ./
COPY packages ./packages
RUN npm ci
# The browser loads the Advisor remote from this URL, so it must be reachable from the user's machine.
ARG PDA_ADVISOR_URL=http://localhost:3001
ENV PDA_ADVISOR_URL=$PDA_ADVISOR_URL
RUN npm run build
EXPOSE 3000 3001
CMD ["npm", "run", "preview"]
