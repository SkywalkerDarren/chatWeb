# Use an official Python runtime as a parent image
FROM python:3.9

# Set the working directory to /app
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install Dependencies
RUN pip3 install -r requirements.txt

# Copy the rest of the application's code
COPY . .

# Make port 7860 and 9531 available to the world outside this container
EXPOSE 7860
EXPOSE 9531

# Run the application when the container launches
CMD ["sh", "run.sh"]
