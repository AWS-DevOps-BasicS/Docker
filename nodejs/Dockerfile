# Use Node 16 alpine as parent image
FROM node:16-alpine
COPY ./chucknorris ./chucknorris
WORKDIR /chucknorris
# Install dependencies
RUN npm install
# Expose application port
EXPOSE 3000
# Start the application
CMD ["npm", "run", "dev"]