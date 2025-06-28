FROM obolibrary/robot:v1.9.8

WORKDIR /tools

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        jq \
        python-is-python3 \
        python3 \
        python3-pip \
        python3-venv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


# Copy the OBO Dashboard source code
COPY requirements.txt .
# The flag 'break-system-packages' is needed to allow installing packages outside the virtual environment in some recent pip versions
RUN python3 -m pip install -r requirements.txt --break-system-packages

# Copy the OBO Dashboard source code
COPY . .

RUN chmod +x obodash
