import { PrismaClient } from '@prisma/client';
import { PrismaNeon } from '@prisma/adapter-neon';
import { neonConfig } from '@neondatabase/serverless';
import ws from 'ws';
import bcrypt from 'bcryptjs';
import fs from 'fs';
import path from 'path';

// Parse .env manually to get DATABASE_URL
const envPath = path.resolve(process.cwd(), '.env');
if (fs.existsSync(envPath)) {
  const envContent = fs.readFileSync(envPath, 'utf-8');
  envContent.split('\n').forEach(line => {
    const match = line.match(/^([^=]+)=(.*)$/);
    if (match) {
      let val = match[2].trim();
      if (val.startsWith('"') && val.endsWith('"')) val = val.slice(1, -1);
      process.env[match[1].trim()] = val;
    }
  });
}

neonConfig.webSocketConstructor = ws;

async function main() {
  if (!process.env.DATABASE_URL) {
    throw new Error("DATABASE_URL is not set in .env");
  }

  const adapter = new PrismaNeon({ connectionString: process.env.DATABASE_URL });
  const prisma = new PrismaClient({ adapter });

  console.log("Connecting to database...");

  const email = "dreamer@zinxx.com";
  const passwordPlain = "password123";
  const name = "Dreamer Demo";
  const hashedPassword = await bcrypt.hash(passwordPlain, 10);

  console.log(`Upserting user: ${email}...`);
  const user = await prisma.user.upsert({
    where: { email },
    update: {
      password: hashedPassword,
      name
    },
    create: {
      email,
      password: hashedPassword,
      name
    }
  });

  console.log(`User ready! ID: ${user.id}`);

  const inputText = "I was in a dark forest running away from a shadow that looked like a wolf, but when I turned around it was a little girl holding a red balloon.";
  const lens = "psychological";

  const storyData = {
    title: "The Wolf and the Red Balloon",
    lens: "psychological",
    characters: [
      { id: "dreamer", name: "Dreamer", role: "first-person protagonist running in panic" },
      { id: "wolf_shadow", name: "Shadow Wolf", role: "pursuing shadow in the dark forest" },
      { id: "little_girl", name: "Little Girl", role: "transformed symbol holding a red balloon" }
    ],
    scenes: [
      {
        id: 1,
        layer: "Subconscious Flight & Fear",
        setting: "a dark, dense forest with twisted branches and thick fog",
        emotional_tone: "panic, breathless flight, dread",
        lines: [
          { speaker: "dreamer", text: "I was in a dark forest running away from a shadow that looked like a wolf. I could hear the branches snapping behind me as it drew closer." }
        ],
        sound_cues: [
          { type: "ambient", prompt: "howling wind through dark pines, rustling leaves, eerie night forest" },
          { type: "one-shot", prompt: "heavy footsteps running on twigs, distant wolf growl", position: "before line 1" }
        ]
      },
      {
        id: 2,
        layer: "Symbolic Transformation & Revelation",
        setting: "a moonlit clearing bathed in stillness and pale mist",
        emotional_tone: "astonishment, eerie calm, wonder",
        lines: [
          { speaker: "dreamer", text: "When I turned around to face it, the shadow dissolved. Standing right there was just a little girl, looking up at me, holding a red balloon." }
        ],
        sound_cues: [
          { type: "music", prompt: "gentle music box chime, ethereal synth pad, resolving tension" },
          { type: "one-shot", prompt: "soft wind chime, balloon rubber squeak", position: "during line 1" }
        ]
      }
    ],
    audio_url: "/output/output.mp3",
    qa_report: {
      consistency_score: 98,
      issues: []
    }
  };

  // Check if this dream already exists for this user to avoid duplicates
  const existingDreams = await prisma.dream.findMany({
    where: {
      userId: user.id,
      inputText
    }
  });

  let dream;
  if (existingDreams.length > 0) {
    console.log("Updating existing dream...");
    dream = await prisma.dream.update({
      where: { id: existingDreams[0].id },
      data: {
        storyData,
        lens,
        isFavorite: true
      }
    });
  } else {
    console.log("Creating new dream...");
    dream = await prisma.dream.create({
      data: {
        userId: user.id,
        inputText,
        storyData,
        lens,
        isFavorite: true
      }
    });
  }

  console.log(`Dream successfully added to Vault! ID: ${dream.id}`);
  await prisma.$disconnect();
}

main().catch(err => {
  console.error("Seeding error:", err);
  process.exit(1);
});
