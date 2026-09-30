// Run this ONCE (node register-commands.js) after setting your .env values,
// and again any time you change the command's name/description/options.
// Registering globally can take up to an hour to propagate on Discord's
// side; if you need it instantly for testing, register per-guild instead
// (see the commented-out guild URL below).

// dotenv is a devDependency and is absent from the deployed function, where
// the values arrive as real environment variables instead.
try {
  await import('dotenv/config');
} catch {
  // No .env loader available — rely on the ambient environment.
}

const APPLICATION_ID = process.env.DISCORD_APPLICATION_ID;
const BOT_TOKEN = process.env.DISCORD_BOT_TOKEN;

if (!APPLICATION_ID || !BOT_TOKEN) {
  console.error('Missing DISCORD_APPLICATION_ID or DISCORD_BOT_TOKEN in .env');
  process.exit(1);
}

const command = {
  name: 'fingerprint',
  description: 'A quiet little check-in.',
  type: 1, // CHAT_INPUT (slash command)

  // The bot is installed to the CTF server so players can SEE it in the
  // member list — its username is the clue. Discovery is the point of it
  // being there; it is not meant to be used there.
  //   0 = GUILD_INSTALL — added to the server by an admin
  integration_types: [0],

  // ...but the command itself is DM-only. Sharing a server with the bot is
  // what grants a player the ability to DM it, so server presence plus
  // BOT_DM gives exactly the intended flow: spot it in the member list,
  // then message it privately.
  //   1 = BOT_DM — direct message with the bot, and nowhere else
  // Omitting 0 (GUILD) means /fingerprint will not appear or run in any
  // server channel. Replaces the deprecated `dm_permission`.
  contexts: [1],
};

// Global registration (works everywhere, slow to propagate ~1hr):
const url = `https://discord.com/api/v10/applications/${APPLICATION_ID}/commands`;

// Guild-only registration (instant, good for testing — uncomment and set
// GUILD_ID in .env if you want this instead):
// const url = `https://discord.com/api/v10/applications/${APPLICATION_ID}/guilds/${process.env.GUILD_ID}/commands`;

async function registerCommand() {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      Authorization: `Bot ${BOT_TOKEN}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(command),
  });

  const data = await response.json();

  if (!response.ok) {
    console.error('Failed to register command:', data);
    process.exit(1);
  }

  console.log('Command registered successfully:', data);
}

registerCommand();
