FROM public.ecr.aws/lambda/python:3.11 AS pip-builder
WORKDIR /opt
RUN mkdir python \
 && cd python \
 && pip install --no-cache-dir -t .  requests urllib3 Jinja2 redis pytz BeautifulSoup4 feedparser \
 && cd ../

FROM public.ecr.aws/lambda/python:3.11
COPY --from=pip-builder /opt/python /opt/python
COPY lambda_function.py ${LAMBDA_TASK_ROOT}
CMD [ "lambda_function.lambda_handler" ]
