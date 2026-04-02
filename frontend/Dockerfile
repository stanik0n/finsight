FROM node:20-alpine AS build

WORKDIR /app

ARG VITE_LOGO_DEV_TOKEN
ARG VITE_CLERK_PUBLISHABLE_KEY

ENV VITE_LOGO_DEV_TOKEN=$VITE_LOGO_DEV_TOKEN
ENV VITE_CLERK_PUBLISHABLE_KEY=$VITE_CLERK_PUBLISHABLE_KEY

COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
