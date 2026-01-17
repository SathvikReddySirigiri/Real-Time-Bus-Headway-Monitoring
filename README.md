# Real-Time Bus Headway Monitoring

## Technology: Spark Streaming with Kafka and MongoDB

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
- [Usage](#usage)
- [Use Case Description](#use-case-description)
- [Organizational Benefits](#organizational-benefits)
- [Architectural Patterns](#architectural-patterns)
- [Troubleshooting](#troubleshooting)
- [References](#references)

## Overview

Real-time Streaming Data Pipeline for bus headway analytics using Kafka, Spark, and MongoDB. Our pipeline processes live GPS data to measure the time gap between consecutive buses on the same route and detect irregularities such as bunching (buses too close together) or gaps (buses too far apart).

**Technology Stack:**

- Kafka: A distributed messaging system for building real-time data pipelines and streaming applications.
- Spark: A unified analytics engine for big data processing, with built-in modules for streaming, SQL, machine learning, and graph processing.
- MongoDB: A NoSQL database for storing and retrieving unstructured data, ideal for handling diverse data types and large volumes.

**Use Case:** Real-time monitoring of bus headways to optimize public transportation efficiency.

## Architecture

[Insert architecture diagram here - can be ASCII art, image, or description]

```css
[GPS Generator] --------> [Kafka] ------------> [Spark Streaming]  ----------------> [MongoDB]
 (Synthesized)            (stream)        (headways,alerts and analytics)            (storage)
```

**Architecture Description:**

- **GPS Generator**: Simulates real-time GPS data for buses.
- **Kafka**: Streams live GPS data from buses in real time.
- **Spark Streaming**: Reads data from Kafka, calculates bus headways, and detects bunching or gaps.
- **MongoDB**: Stores the processed results and alerts for analysis and visualization in Jupyter.

## Prerequisites

**System Requirements:**

- Docker Engine 20.10+
- Docker Compose 2.0+
- Minimum 8GB RAM
- 20GB free disk space

**Ports Used:**

- Port 2181: Zookeeper
- Port 9092: Kafka (External)
- port 29092: Kafka (Internal)
- Port 7077: Spark Master
- Port 8080: Spark Master
- Port 8081: Spark Worker 1
- Port 8082: Spark Worker 2
- Port 8888: Jupyter Notebook
- Port 27017: MongoDB

## Setup Instructions

### Step 1: Clone or Extract Project

```bash
cd data-buddies-final-project/
```

### Step 2: Start the Cluster

```bash
docker compose up -d
```

### Step 3: Verify Services

```bash
docker compose ps
```

All services should show as "running" and Mongo/Zk as "healthy".

### Step 4: Access Services

- Spark Master UI: http://localhost:8080
- Spark Worker 1 UI: http://localhost:8081
- Spark Worker 2 UI: http://localhost:8082
- Jupyter Notebook: http://localhost:8888
- MongoDB: http://localhost:27017
- Kafka Boostrap:
  - External: localhost:9092
  - Internal: kafka:29092

### Step 5: Run the Demonstration

Access Jupyter at http://localhost:8888
(token: spark)

## Usage

### Basic Operations

#### 1) Kafka checks

```bash
# List topics (host -> Kafka EXTERNAL)
docker exec -it kafka bash -lc 'kafka-topics --bootstrap-server kafka:9092 --list'

# Create the gps topic (if your simulator doesn't auto-create)
docker exec -it kafka bash -lc 'kafka-topics --bootstrap-server kafka:9092 --create --topic gps --partitions 3 --replication-factor 1'

# Describe topic
docker exec -it kafka bash -lc 'kafka-topics --bootstrap-server kafka:9092 --describe --topic gps'
```

#### 2) MongoDB checks

```bash
# Open mongosh
docker exec -it mongo mongosh -u admin -p password --authenticationDatabase admin

# In mongosh:
use transit
db.runCommand({ ping: 1 })
show collections
db.service_alerts.find().sort({arrival_time:-1}).limit(3).pretty()
```

#### 4) Jupyter Container shell

```bash
docker exec -it spark-jupyter bash
```

### Running the Demo

The `demonstration.ipynb` notebook walks through:

1. **Cluster Health**: Verify Kafka, Spark Master UI, and MongoDB connectivity (ping & client checks).
2. **Data Ingestion**: Start the synthetic GPS simulator producing to Kafka topic gps.
3. **Stream Processing**: Launch Spark Structured Streaming jobs to:
   - Match GPS points to stops,
   - Compute headways with stateful logic,
   - Generate real-time service alerts (bunching/gaps),
   - Aggregate hourly performance metrics.
4. **Persistence & Analysis**: Write results to MongoDB (headway_metrics, service_alerts, daily_performance) and visualize/inspect inside the notebook.

## Use Case Description

### Problem Statement

Public transportation systems often face a common problem called "bus bunching," where two or more buses on the same route get too close together. This happens because once one bus is delayed, it picks up more passengers, stops longer, and slows down further, while the next bus behind it cathes up.

Beacuase of this, passengers experience long waits followed by multiple buses arriving at once (or with very short gaps). This reduces service reliability and increases operational costs.

### Solution Approach

We built a real-time streaming pipeline that continuously tracks bus positions and calculates headways. our system works like this:

A Python GPS generator simulates live bus location data. (synthesized data for demonstration purposes)
Kafka streams this data reliably in real time.
Spark Structured Streaming processes the data, calculating headways and detecting bunching or gaps.
MongoDB stores the results and alerts for further analysis.
From the data stored in MongoDB, we can visualize and analyze bus performance over time.

### Data Flow

1. **Ingestion**: Simulated GPS data is sent to Kafka in real time.
2. **Processing**: Spark Structured Streaming reads data from Kafka, calculates headways, and detects bunching or gaps.
3. **Storage**: MongoDB stores the processed results and alerts for analysis.
4. **Analysis**: Jupyter notebooks are used to visualize and analyze bus performance over time.

### Sample Data

- **Source**: Simulated GPS data from buses
- **Size**: Continuous stream of location updates
- **Format**: JSON
- **Schema**:
  - `timestamp`: Time of the GPS reading
  - `route_id`: Identifier for the bus route
  - `vehicle_id`: Unique identifier for each bus
  - `direction`: Direction of travel (0 or 1)
  - `latitude`: Latitude coordinate
  - `longitude`: Longitude coordinate
  - `speed`: Current speed of the bus

## Organizational Benefits

### Scalability

- **Kafka**: It can be scaled by adding more partitions to the `gps` topic and brokers. More partitions means more parallel Spark Consumers.
- **Spark**: Add workers and cores to increase parallelism.
- **MongoDB**: **replica set** increases durability. **sharding** (by `route_id` or time) when writes/reads grow.

### Performance

Processes live data with low latency and high throughput.

### Reliability

- Using replication and fault tolerance mechanisms.
- Kafka provides data replication across multiple brokers, ensuring no data loss.
- Spark Structured Streaming can recover from failures by reprocessing data from Kafka.

### Cost Efficiency

Using open-source tools inside Docker containers keeps infrastructure and licensing costs low while allowing efficient resource sharing.

### Business Value

Our setup enables **real-time transit monitoring**, helping transportation agencies improve **service reliability**, **schedule planning**, and **passenger satisfaction** through faster insights and better operational control.

## Architectural Patterns

### Where This Technology Fits

This setup follows the **Kappa Architecture**, where all data is processed as a continuous stream. It is commonly used in:

- **Real-time Analytics Pipelines** – For processing live data like GPS or sensor feeds.
- **Event-driven Systems** – Where actions or alerts are triggered as data arrives.
- **Monitoring Dashboards** – For showing live metrics, trends, or alerts in real time.

### Real-World Examples

- **Uber**: Uses Kafka and Spark to process live trip and GPS data for dynamic pricing and driver tracking.
- **Netflix**: Streams events through Kafka for monitoring and recommendations.
- **LinkedIn**: Built Kafka originally to handle billions of messages per day for activity tracking.

### When to Use This Technology

**Good fit for:**

- Real-time streaming data (IoT, GPS, transactions).
- Continuous monitoring or alerting systems.
- Scenarios needing low latency and scalable processing.

**Not recommended for:**

- Small or static datasets that can be processed in batches.
- Applications requiring heavy relational joins or complex transactions.

## Troubleshooting

### Services Won't Start

**Problem**: Containers exit immediately or show “unhealthy.”

**Solution**: Check the service logs for errors and ensure all dependencies are running.

### Connection Errors

**Problem**: Services cannot connect to Kafka or MongoDB.

**Solution**:

- Check Kafka bootstrap URL.
  - If running in Docker, use `kafka:9092` for internal connections, use `localhost:9092` for external.
  - For MongoDB, use `mongodb://admin:password@mongo:27017/?authSource=admin`.

### Performance Issues

**Problem**: Streams run slow or Spark crashes.

**Solution**:

- Lower the simulator rate or reduce number of buses.
- Use fewer memory sinks — write directly to Mongo instead.
- Add more Spark workers or increase driver memory in compose file.
- Restart the cluster to clear checkpoints if needed.

### Checking Logs

```bash
# View logs for a specific service
docker compose logs [service-name]

# Follow logs in real-time
docker compose logs -f [service-name]

# View last 100 lines
docker compose logs --tail=100 [service-name]
```

common logs to check:

- `docker compose logs kafka` check if Kafka started properly
- `docker compose logs spark-master` check job submissions
- `docker compose logs mongo` confirm DB connections
- `docker compose logs spark-jupyter` see notebook startup and Spark link

## References

- [Kafka DockerHub](https://hub.docker.com/r/apache/kafka)
- [Python Client for Kafka](https://docs.confluent.io/kafka-clients/python/current/overview.html)
- [Spark DataFrames](https://spark.apache.org/docs/latest/streaming/apis-on-dataframes-and-datasets.html)
- [Spark Structured Streaming](https://spark.apache.org/docs/latest/streaming/structured-streaming-kafka-integration.html)
- [Tutorial: A Beginner’s Guide to Kafka with Python: Real-Time Data Processing and Applications](https://medium.com/@keshavmanglore/article-a-beginners-guide-to-kafka-with-python-real-time-data-processing-and-applications-5db39b320f3e)
- [Tutorial: A Fast Look at Spark Structured Streaming + Kafka](https://towardsdatascience.com/a-fast-look-at-spark-structured-streaming-kafka-f0ff64107325/)

---

## Project Statistics

- **Lines of Code**: [Approximate]
- **Number of Services**: 7
- **Dataset Size**: Continuous GPS stream (~10,000 simulated points)
- **Development Time**: 4.5 days

## Author

**Name**: Data Buddies: Mahammad Siraj Cheruvu, Aravind Polavapu, Naga Pavan Sathvik Reddy Sirigiri
**Date**: 9 November 2025
**Course**: Big Data for Business
