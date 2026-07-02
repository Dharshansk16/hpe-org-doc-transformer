const amqp = require("amqplib");
const dispatch = require("./dispatcher");
const { setupQueues } = require("../queue/rabitMQ");

async function start() {
  const connection = await amqp.connect("amqp://localhost");
  const channel = await connection.createChannel();

  //re-assert queues with DLX args
  await setupQueues(channel);

  console.log("Consumer running...");

  channel.consume("event_queue", async (msg) => {
    if (!msg) return;

    try {
      const data = JSON.parse(msg.content.toString());
      await dispatch(data, channel);
      channel.ack(msg);
    } catch (err) {
      console.error(
        "[Consumer Error] Failed to dispatch message:",
        err.message,
      );
      // Nack and DO NOT requeue -> this sends it to DLQ via DLX configuration!
      channel.nack(msg, false, false);
    }
  });
}

start();
