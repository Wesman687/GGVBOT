const { Client, GatewayIntentBits } = require("discord.js");
const {
  joinVoiceChannel,
  EndBehaviorType,
  createAudioPlayer,
  createAudioResource,
  entersState,
  AudioPlayerStatus,
  getVoiceConnection
} = require("@discordjs/voice");
const prism = require("prism-media");
const WebSocket = require("ws");
const fs = require("fs");
require("dotenv").config();

const DISCORD_TOKEN = process.env.DISCORD_TOKEN;
const GUILD_ID = process.env.GUILD_ID;
const VC_CHANNEL_ID = process.env.VC_CHANNEL_ID;
const WS_URL = process.env.WS_URL || "ws://localhost:8765";

let ws;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 100;
const RECONNECT_INTERVAL = 5000;

const activeStreams = new Map()

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildVoiceStates,
  ],
});

function cleanupStreams() {
  for (const { opusStream, decoder, onData } of activeStreams.values()) {
    decoder.removeListener("data", onData);
    opusStream.destroy();
    decoder.destroy();
  }
  activeStreams.clear();
}

async function shutdown() {
  try {
    const connection = getVoiceConnection(GUILD_ID);
    if (connection) {
      console.log("📴 Leaving voice channel...");
      cleanupStreams();
      connection.destroy();
    }
    console.log("👋 Shutting down Node.js bot...");
    process.exit(0);
  } catch (err) {
    console.error("❌ Error during shutdown:", err);
    process.exit(1);
  }
}

function connectWebSocket() {
  ws = new WebSocket(WS_URL);

  ws.on("open", () => {
    console.log(`🌐 Connected to WebSocket server at ${WS_URL}`);
    reconnectAttempts = 0;
  });

  ws.on("error", (err) => {
    console.error(`❌ WebSocket error: ${err.message}`);
  });

  ws.on("close", () => {
    console.warn("🔌 WebSocket disconnected.");
    if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
      reconnectAttempts++;
      console.log(`🔁 Reconnecting in ${RECONNECT_INTERVAL / 1000}s... (attempt ${reconnectAttempts})`);
      setTimeout(connectWebSocket, RECONNECT_INTERVAL);
    } else {
      console.error("❌ Max reconnect attempts reached. Giving up.");
    }
  });

  ws.on("message", async (data) => {
    try {
      const msg = JSON.parse(data);

      if (msg.type === "shutdown") {
        console.log(`👋 Received shutdown message from ${msg.user}`);
        await shutdown();
      }

      if (msg.type === "speak" && msg.user && msg.audio && msg.format === "wav") {
        const buffer = Buffer.from(msg.audio, "base64");
        const path = `jarvis_reply_${msg.user.replace(/[#]/g, "")}.wav`;
        fs.writeFileSync(path, buffer);

        const player = createAudioPlayer();
        const resource = createAudioResource(path);
        const voiceConnection = getVoiceConnection(GUILD_ID);

        if (!voiceConnection) {
          console.warn("⚠️ No active voice connection to play audio");
          return;
        }

        voiceConnection.subscribe(player);
        player.play(resource);

        await entersState(player, AudioPlayerStatus.Playing, 5000);
      }
    } catch (err) {
      console.error(`❌ Failed to handle speak message: ${err.message}`);
    }
  });
}

client.once("ready", async () => {
  console.log(`🤖 Logged in as ${client.user.tag}`);

  const guild = await client.guilds.fetch(GUILD_ID);
  const vc = await guild.channels.fetch(VC_CHANNEL_ID);

  if (!vc || vc.type !== 2) {
    console.error("❌ Voice channel not found or invalid.");
    return;
  }

  const connection = joinVoiceChannel({
    channelId: vc.id,
    guildId: guild.id,
    adapterCreator: guild.voiceAdapterCreator,
    selfDeaf: false,
  });

  console.log(`🎙️ Connected to voice channel: ${vc.name}`);
  connectWebSocket(); // 🔗 Resilient websocket logic

  connection.receiver.speaking.on("start", async (userId) => {
    if (activeStreams.has(userId)) return; // ✅ Already tracking, skip re-subscribe
  
    try {
      const user = await client.users.fetch(userId);
      const username = `${user.username}#${user.discriminator}`;
      console.log(`🎙️ Subscribing to ${username}`);
  
      const opusStream = connection.receiver.subscribe(userId, {
        end: { behavior: EndBehaviorType.Manual }, // ♾️ Keep alive
      });
  
      const decoder = new prism.opus.Decoder({
        rate: 48000,
        channels: 1,
        frameSize: 960,
      });
  
      opusStream.pipe(decoder);
  
      const onData = (chunk) => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            user: username,
            audio: chunk.toString("base64"),
          }));
        }
      };
  
      decoder.on("data", onData);
  
      activeStreams.set(userId, {
        opusStream,
        decoder,
        onData,
      });
  
      opusStream.once("close", () => {
        console.log(`📴 Stream closed for ${username}`);
        decoder.removeListener("data", onData);
        activeStreams.delete(userId);
        decoder.destroy();
      });
  
    } catch (err) {
      console.error(`❌ Failed to subscribe to ${userId}: ${err.message}`);
    }
  });
});

client.login(DISCORD_TOKEN);
