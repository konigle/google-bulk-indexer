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

## Before you run the tool

Follow the [guide by Google Cloud](https://developers.google.com/search/apis/indexing-api/v3/prereqs) to setup Google Cloud account and service account. You should have the following by the end:

- A google cloud account with a project that has both `Google Search Console API` and `Web Search Indexing API` enabled.
- A service account and a private key json file downloaded on your PC.
- The service account email added to your property (site) as Site owner.

## Running the tool

1. Install the package

```bash
pip install gsc-bulk-indexer
```

3. Copy the private key file that you downloaded from the Google cloud account in the same folder from which you are going to run the tool. Private key is needed for submitting URLs to Google Search Console for indexing.
4. Run the following command to start submitting URLs for indexing

   - If you have verified your site as a `Domain` property in GSC run the following command

   ```bash
   gsc_bulk_index -p <your-domain.xyz>
   ```

   OR

   ```bash
   python -m gsc_bulk_indexer.submit -p <your-domain.xyz>
   ```

   - If you have verified your site as a `URL Prefix` property, run the below command

   ```bash
   gsc_bulk_index -p https://<your-domain.xyz>
   ```

If you have the private key json file somewhere else on your PC, you can specify
the path while running the script

```bash
gsc_bulk_index -c <path to private key file> -p <site domain>
```

Run the script with `--help` to know about command line options.

## Use in your application

The indexer comes with caching mechanism to avoid submitting URLs
that have already been submitted. It creates pickle files under `.cache` directory in the current working directory. However, if you using the bulk indexer in your application backend, this might not be needed. Below is the recommended usage of the indexer in your application.

```python
from gsc_bulk_indexer import auth
from gsc_bulk_indexer import indexer

def index():
   credentials = {
      # service account json key dictionary
   }
   # submit the property URL
   gsc_property = "https://example.com"
   # OR submit a list of URLs
   # urls = ["https://example.com/page1", "https://example.com/page2"]
   access_token = auth.get_access_token(credentials=credentials)
   if access_token is None:
      return

   gsc_indexer = indexer.BulkIndexer(
      access_token,
      property=gsc_property,
      # urls=urls, # if you want to submit a list of URLs
      use_cache=False, # disable cache to prevent cache files from being created
   )
   num_urls_submitted = gsc_indexer.index()
```
