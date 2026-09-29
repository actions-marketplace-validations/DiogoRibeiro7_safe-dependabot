FROM python:3.14-alpine

WORKDIR /action

COPY requirements.txt /action/requirements.txt
RUN pip install --no-cache-dir -r /action/requirements.txt

COPY src /action/src

ENTRYPOINT ["python", "/action/src/validate.py"]
