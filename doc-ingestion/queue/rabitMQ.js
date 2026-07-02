const amqp = require("amqplib");
let channel;

async function setupQueues(ch) {
  const DLX_NAME = "dlx_exchange";
  const DLQ_NAME = "dead_letter_queue";

  await ch.assertExchange(DLX_NAME, "direct", { durable: true });
  await ch.assertQueue(DLQ_NAME, { durable: true });
  //route any message to DLX to this DLQ
  await ch.bindQueue(DLQ_NAME, DLX_NAME, "failed_messages");

  const queueArgs = {
    durable: true,
    deadLetterExchange: DLX_NAME,
    deadLetterRoutingKey: "failed_messages",
  };

  await ch.assertQueue("event_queue", queueArgs);
  await ch.assertQueue("normalization_queue", queueArgs);
  await ch.assertQueue("normalized_events", queueArgs);
}

async function connectQueue() {
  const connection = await amqp.connect("amqp://localhost");
  channel = await connection.createChannel();

  await setupQueues(channel);

  console.log("RabbitMQ connected and DLX queues setup");
}

async function pushToQueue(data) {
  if (!channel) {
    console.log("Channel not ready");
    return;
  }

  const result = channel.sendToQueue(
    "event_queue",
    Buffer.from(JSON.stringify(data)),
    { persistent: true },
  );

  console.log("Send result:", result);
  console.log("Message pushed");
}

module.exports = {
  connectQueue,
  pushToQueue,
  setupQueues,
};
