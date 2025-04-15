const { Client, GatewayIntentBits } = require("discord.js");
const {
  joinVoiceChannel,
  EndBehaviorType,
} = require("@discordjs/voice");
const prism = require("prism-media");
const WebSocket = require("ws");
require("dotenv").config();

const DISCORD_TOKEN = process.env.DISCORD_TOKEN;
const GUILD_ID = process.env.GUILD_ID;
const VC_CHANNEL_ID = process.env.VC_CHANNEL_ID;
const WS_URL = process.env.WS_URL || "ws://localhost:8765";

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildVoiceStates,
  ],
});

let ws;

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

  // 🔗 Connect to Python WebSocket
  ws = new WebSocket(WS_URL);

  ws.on("open", () => {
    console.log(`🌐 Connected to WebSocket server at ${WS_URL}`);
  });

  ws.on("error", (err) => {
    console.error(`❌ WebSocket error: ${err.message}`);
  });

  // 🔉 When someone starts speaking
  connection.receiver.speaking.on("start", async (userId) => {
    try {
      const user = await client.users.fetch(userId);
      const username = `${user.username}#${user.discriminator}`;
      console.log(`👂 Voice activity started from: ${username}`);

      const opusStream = connection.receiver.subscribe(userId, {
        end: {
          behavior: EndBehaviorType.AfterSilence,
          duration: 1000,
        },
      });

      const pcmStream = new prism.opus.Decoder({
        channels: 1,
        rate: 48000,
        frameSize: 960,
      });

      opusStream.pipe(pcmStream);

      pcmStream.on("data", (chunk) => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            user: username,
            audio: chunk.toString("base64"),
          }));
        }
      });

    } catch (err) {
      console.error(`❌ Error subscribing to user audio: ${err.message}`);
    }
  });
});

client.login(DISCORD_TOKEN);
