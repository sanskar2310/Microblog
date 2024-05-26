# Use the official Python image from the Docker Hub
FROM python:slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install the Python dependencies
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
RUN pip install gunicorn

# Copy the rest of the application code to the container
COPY app app
COPY migrations migrations
COPY microblog.py config.py boot.sh ./
RUN chmod a+x boot.sh

# Set environment variables
ENV FLASK_APP microblog.py


# Expose port 5000 to the outside world
EXPOSE 5000

# Define the command to run the application
ENTRYPOINT ["./boot.sh"]
