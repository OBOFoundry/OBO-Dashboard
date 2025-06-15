FROM obolibrary/robot:latest

WORKDIR /tools

# Install system dependencies
RUN apt-get update && \
    apt-get install -y git \
        python3 \
        python3-pip \
        python3-venv \
        python-is-python3 \
        jq && \
    rm -rf /var/lib/apt/lists/*


# Copy the OBO Dashboard source code
COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt --break-system-packages
COPY . .
