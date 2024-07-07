# InteliSort

Bangkok City Incident and Issue AI Powered Prioritization and Sorting system Implemented by CEDT student

## Setup

### Pre-requisites

assumes you have the following installed:

-   pyenv
-   poetry
-   Docker
-   Docker Compose

```bash
poetry install
cp .env.example .env # Copy the example environment file, then fill in the values
docker-compose up -d # Start the database
poetry run prisma generate && poetry run prisma db push
```

## Start the server

```bash
docker-compose up -d # Start the database
# EXPORT PORT=8000 or set change the $PORT variable in the command below (recommended)
PORT=8000 poetry run gunicorn -w 1 -k uvicorn.workers.UvicornWorker --bind "[::]:$PORT" app.main:app --timeout 300
# mac user & linux user can use the following command
chmod +x ./run.sh
PORT=8000 ./run.sh
```

## Build Docker Image

```bash
# docker build -t path/to/image:tag .
docker buildx build -t path/to/image:tag . --platform linux/amd64 # For multi-architecture builds, make sure to have buildx enabled
```

## Services

### similarity and distance query

#### upload csv to database on (parse to multipart/from-data)

recommend uploading on [swagger](http://localhost:8000/docs#/1.%20import%20data/import_csv_intelisort_import_csv_post) or postman

-   /intelisort/import/csv
    ```json
        csv_file *string($binary)
    ```

#### Check status of the uploaded file

check the status of the uploaded file [swagger](http://localhost:8000/docs#/intelisort/get_index_info_intelisort_index_info_get)

-   /intelisort/index_info
    -   response
        ```json
        {
            "success": true,
            "content": "994 docs (100.0%) indexed w/ 0 failures in 72.63 msecs"
        }
        ```

### query from similarity

query data from similarity [swagger](http://localhost:8000/docs#/2.%20query%20data/query_data_from_similarity_intelisort_query_from_similarity_post)

-   /intelisort/query_from_similarity
    -   request
        ```json
        {
            "queries": [
                {
                    "ticket_id": "2024-DRA89Z",
                    "type": "{ป้าย,ความสะอาด,ถนน}",
                    "organization": "เขตคันนายาว",
                    "comment": "แจ้งป้ายเถื่อน ป้ายกองโจร :scream: ติดป้าย ผิด พรบ.ความสะอาด และความเป็นระเบียบเรียบร้อยของบ้านเมือง",
                    "coords": "100.66948,13.85152",
                    "photo": "https://storage.googleapis.com/traffy_public_bucket/attachment/2024-02/bdc9d2c2fb53e48438071804a6619438545860a9.jpg",
                    "photo_after": null,
                    "address": "3 ซ. คู้บอน 26 คันนายาว เขตคันนายาว กรุงเทพมหานคร 10230 ประเทศไทย",
                    "subdistrict": "รามอินทรา",
                    "district": "คันนายาว",
                    "province": "กรุงเทพมหานคร",
                    "timestamp": "2024-02-03 12:29:05.727076+00",
                    "state": "รอรับเรื่อง",
                    "star": null,
                    "count_reopen": 0,
                    "last_activity": "2024-02-03 12:29:05.716382+00"
                }
            ],
            "top_k": 3
        }
        ```
    -   response
        ```json
        {
            "success": true,
            "content": [
                [
                    {
                        "similarity_score": 0.735,
                        "state": "กำลังดำเนินการ",
                        "comment": "ป้ายกองโจรริมถนน ผิดพรบ.ความสะอาดพ.ศ.2535 ช่วยมาเก็บด่วน\r\n#1555 #bkkrongtook",
                        "type": "ป้าย,ความสะอาด",
                        "address": "PCCH+C84 แขวงบางด้วน เขตภาษีเจริญ กรุงเทพมหานคร 10160 ประเทศไทย",
                        "district": "ภาษีเจริญ",
                        "province": "กรุงเทพมหานคร",
                        "subdistrict": "บางด้วน"
                    },
                    {
                        "similarity_score": 0.731,
                        "comment": "ป้ายกองโจร ผิดพรบ.ความสะอาดพ.ศ.2535ติดกันเรียงราย3ป้า โคซี่ป้ายนึง บริษัทหมู่บ้านนายกป้ายนึง นันทวรรณอีกป้าย1 ช่วยมาเก็บด่วน\r\n#1555 #bkkrongtook",
                        ...
                    },
                    {
                        "similarity_score": 0.726,
                        "comment": "แปะป้ายโฆษณาในที่สาธารณะ",
                        ...
                    }
                ]
            ]
        }
        ```

### query from distance

query data from distance [swagger](http://localhost:8000/docs#/2.%20query%20data/query_data_from_distance_intelisort_query_from_distance_post)

-   /intelisort/query_from_distance
    -   request
        ```json
        {
            "queries": [
                {"coords": "100.54896,13.74037"},
                {"coords": "100.54896,13.74037"}
            ],
            "top_k": 5,
            "radius": 600
        }
        ```
    -   response
        ```json
        {
            "success": true,
            "content": [
                [
                    {
                        "distance": 305.2487,
                        "latitude": 100.55020898580551,
                        "longitude": 13.742831025420443,
                        "data": {
                            "ticket_id": "2024-FKRZM6",
                            ...
                            "coords": "100.55021,13.74283",
                            "address": "111 ถนน เพลินจิต แขวงลุมพินี เขตปทุมวัน กรุงเทพมหานคร 10330 ประเทศไทย",
                            "subdistrict": "ลุมพินี",
                            "district": "ปทุมวัน",
                            "province": "กรุงเทพมหานคร",
                            "timestamp": "2024-02-03 04:06:36.048676+00",
                            "state": "กำลังดำเนินการ",
                            "star": "",
                            "count_reopen": "0",
                            "last_activity": "2024-02-03 07:17:37.683482+00"
                        }
                    },
                    {
                        "distance": 345.301,
                        "latitude": 100.5475589632988,
                        "longitude": 13.743160539171157,
                        "data": {
                            ...
                        }
                    },
                [
                    {
                        "distance": 305.2487,
                        "latitude": 100.55020898580551,
                        "longitude": 13.742831025420443,
                        "data": {
                            "ticket_id": "2024-FKRZM6",
                            "coords": "100.55021,13.74283",
                            ...
                            "address": "111 ถนน เพลินจิต แขวงลุมพินี เขตปทุมวัน กรุงเทพมหานคร 10330 ประเทศไทย",
                            "subdistrict": "ลุมพินี",
                            "district": "ปทุมวัน",
                            "province": "กรุงเทพมหานคร",
                            "timestamp": "2024-02-03 04:06:36.048676+00",
                            "state": "กำลังดำเนินการ",
                        }
                    },
                    {
                        "distance": 345.301,
                        "latitude": 100.5475589632988,
                        "longitude": 13.743160539171157,
                        "data": {
                            ...
                        }
                    },
                ]
                ]
            ],
        }
        ```
