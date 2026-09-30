import { verifyKey, InteractionType, InteractionResponseType } from 'discord-interactions';

// Discord signs the raw request bytes, so we must read the stream ourselves
// and verify against exactly those bytes — re-serialising a parsed object
// would not be byte-identical and every signature check would fail.
function readRawBody(req) {
  return new Promise((resolve, reject) => {
    let data = '';
    req.on('data', (chunk) => {
      data += chunk;
    });
    req.on('end', () => resolve(data));
    req.on('error', reject);
  });
}

const FINGERPRINT_REPLY = [
  "Clever, aren't you, finding me here —",
  "a bot with no face, but I'm still near.",
  "I won't spell out where I've been,",
  "but a name's a name, wherever it's seen.",
  'Look twice at the one who\'s typing this line —',
  'he answers to it everywhere, all the time.',
].join('\n');

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.status(405).send('Method not allowed');
    return;
  }

  const signature = req.headers['x-signature-ed25519'];
  const timestamp = req.headers['x-signature-timestamp'];
  const rawBody = await readRawBody(req);

  const isValidRequest = verifyKey(
    rawBody,
    signature,
    timestamp,
    process.env.DISCORD_PUBLIC_KEY
  );

  if (!isValidRequest) {
    res.status(401).send('Bad request signature');
    return;
  }

  const interaction = JSON.parse(rawBody);

  // Discord's handshake check — required for every interactions endpoint.
  if (interaction.type === InteractionType.PING) {
    res.status(200).json({ type: InteractionResponseType.PONG });
    return;
  }

  if (interaction.type === InteractionType.APPLICATION_COMMAND) {
    const commandName = interaction.data?.name;

    if (commandName === 'fingerprint') {
      res.status(200).json({
        type: InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
        data: {
          content: FINGERPRINT_REPLY,
          // flags: 64 = EPHEMERAL — only the command's caller can see this reply
          flags: 64,
        },
      });
      return;
    }
  }

  res.status(400).send('Unknown interaction type or command');
}
