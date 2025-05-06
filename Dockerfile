ARG PARENT_IMAGE
FROM $PARENT_IMAGE

# Pull in build-arguments
ARG CONTAINER_NAME
ARG MAINTAINER
ARG MAINTAINER_EMAIL
ARG PARENT_IMAGE
ARG PROJECT_VERSION

# Set container labels
LABEL container_name=${CONTAINER_NAME}
LABEL maintainer=${MAINTAINER}
LABEL maintainer_email=${MAINTAINER_EMAIL}
LABEL parent_image=${PARENT_IMAGE}


# Install Requirments
COPY requirements.txt tmp/
RUN python3.11 -m pip install -i https://pypi.ci.artifacts.walmart.com/artifactory/api/pypi/gpa-pypi/simple  -r tmp/requirements.txt
WORKDIR /home/peopleai/genai_plugin_prompt_bridge

COPY src/genai_plugin_prompt_bridge ./
COPY start.sh  ./start.sh

# Copy Private Key if exist
COPY /keys/* ./
ENV PROJECT_VERSION=$PROJECT_VERSION

# Adjust permissions so peopleai user can access without issues
USER root
RUN chmod -R 775 /home/peopleai/genai_plugin_prompt_bridge

# Return to peopleai user
USER peopleai

# Update Python path for project
# TODO: convert to args instead of hardcoded
ENV PYTHONPATH="$PYTHONPATH:/home/peopleai/genai_plugin_prompt_bridge"
ENV PYTHONPATH="$PYTHONPATH:/home/peopleai/"


EXPOSE 8000

CMD ["sh", "start.sh"]
