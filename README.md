# Google Bulk Indexer

Python script for automatically submitting website pages for indexing in bulk to Google Search Console(GSC).
This is a Python version of the original work in [google-indexing-script](https://github.com/goenning/google-indexing-script)

## Functionality

This script submits the website URLs found on a site that you own to GSC for indexing. There is no guarantee that the page requested
for indexing will be indexed by Google.

## Requirements

1. Python >= 3.9
2. A Google Cloud account: You will have to create a service account under
   a Google cloud project and download the private key JSON file.
3. GSC account with a verified site (property).

## Before you run the script

Follow the [guide by Google Cloud](https://developers.google.com/search/apis/indexing-api/v3/prereqs) to setup Google Cloud account and service account. You should have the following by the end:

- A google cloud account with a project that has both `Google Search Console API` and `Web Search Indexing API` enabled.
- A service account and a private key json file downloaded on your PC.
- The service account email added to your property (site) as Site owner.

## Running the script

1. Clone this repository on your local PC which has Python installation.
2. Install the required packages by running the below command

```bash
pip install -r requirements.txt
```

3. Copy the private key file that you downloaded from the Google cloud account
   in the same folder. Private key is needed for submitting URLs to Google Search Console for indexing.
4. Run the following command to start submitting URLs for indexing
   - If you have verified your site as a `Domain` property in GSC run the following command
   ```bash
   python ./main.py -p <your-domain.xyz>
   ```
   - If you have verified your site as a `URL Prefix` property, run the below command
   ```
   python ./main.py -p https://<your-domain.xyz>
   ```

If you have the private key json file somewhere else on your PC, you can specify
the path while running the script

```
python ./main.py -c <path to private key file> -p <site domain>
```

Run the script with `--help` to know about command line options.
