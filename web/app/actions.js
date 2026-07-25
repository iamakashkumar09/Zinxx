'use server'

import { prisma } from '@/lib/prisma'
import { SignJWT, jwtVerify } from 'jose'
import { cookies } from 'next/headers'
import bcrypt from 'bcryptjs'

const SECRET_KEY = new TextEncoder().encode(
  process.env.JWT_SECRET || 'dream_archaeology_secret_key_2026_zinxx_hackathon_default'
);

export async function createJwtSession(user) {
  try {
    const token = await new SignJWT({ id: user.id, email: user.email, name: user.name })
      .setProtectedHeader({ alg: 'HS256' })
      .setIssuedAt()
      .setExpirationTime('7d')
      .sign(SECRET_KEY);

    const cookieStore = await cookies();
    cookieStore.set('jwt_session', token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 60 * 60 * 24 * 7, // 7 days
      path: '/',
    });
    return token;
  } catch (err) {
    console.warn("Could not set cookie:", err.message);
    return null;
  }
}

export async function getSessionUser() {
  try {
    const cookieStore = await cookies();
    const token = cookieStore.get('jwt_session')?.value;
    if (!token) return null;
    const { payload } = await jwtVerify(token, SECRET_KEY);
    return { id: String(payload.id || ''), email: String(payload.email || ''), name: String(payload.name || ''), token };
  } catch (err) {
    return null;
  }
}

export async function logoutUser() {
  try {
    const cookieStore = await cookies();
    cookieStore.delete('jwt_session');
    return { success: true };
  } catch (err) {
    return { success: false };
  }
}

export async function loginUser(email, password) {
  if (!prisma) return null;
  try {
    const user = await prisma.user.findUnique({ where: { email } });
    if (!user) throw new Error("Invalid credentials");
    
    // Securely compare password with bcrypt (includes fallback for any legacy plaintext test accounts)
    const isMatch = await bcrypt.compare(password, user.password).catch(() => false) || (user.password === password);
    if (!isMatch) throw new Error("Invalid credentials");

    const sessionUser = { id: user.id, email: user.email, name: user.name };
    const token = await createJwtSession(sessionUser);
    return { ...sessionUser, token };
  } catch (e) {
    if (e.message === "Invalid credentials") throw e;
    console.warn("Prisma login error:", e.message);
    return null;
  }
}

export async function registerUser(email, password, name) {
  if (!prisma) return null;
  try {
    const existing = await prisma.user.findUnique({ where: { email } });
    if (existing) throw new Error("Email already exists");
    
    // Encrypt password using bcrypt with 10 salt rounds before saving to database
    const hashedPassword = await bcrypt.hash(password, 10);
    const user = await prisma.user.create({ data: { email, password: hashedPassword, name } });
    
    const sessionUser = { id: user.id, email: user.email, name: user.name };
    const token = await createJwtSession(sessionUser);
    return { ...sessionUser, token };
  } catch (e) {
    if (e.message === "Email already exists") throw e;
    console.warn("Prisma register error:", e.message);
    return null;
  }
}

export async function saveDream(userId, inputText, storyData, lens, isFavorite = false) {
  if (!prisma) {
    return {
      id: Date.now().toString(),
      userId,
      inputText,
      storyData,
      lens,
      isFavorite,
      createdAt: Date.now()
    };
  }
  try {
    const dream = await prisma.dream.create({
      data: { userId, inputText, storyData, lens, isFavorite }
    });
    return {
      ...dream,
      createdAt: dream.createdAt ? new Date(dream.createdAt).getTime() : Date.now()
    };
  } catch (e) {
    console.warn("Prisma saveDream error:", e.message);
    return {
      id: Date.now().toString(),
      userId,
      inputText,
      storyData,
      lens,
      isFavorite,
      createdAt: Date.now()
    };
  }
}

export async function getDreams(userId) {
  if (!prisma) return [];
  try {
    const dreams = await prisma.dream.findMany({
      where: { userId },
      orderBy: { createdAt: 'desc' }
    });
    return dreams.map(d => ({
      ...d,
      createdAt: d.createdAt ? new Date(d.createdAt).getTime() : Date.now()
    }));
  } catch (e) {
    console.warn("Prisma getDreams error:", e.message);
    return [];
  }
}

export async function deleteDream(id) {
  if (!prisma) return { id, deleted: true };
  try {
    return await prisma.dream.delete({ where: { id } });
  } catch (e) {
    console.warn("Prisma deleteDream error:", e.message);
    return { id, deleted: true };
  }
}

export async function toggleDreamFavorite(id, isFavorite) {
  if (!prisma) return { id, isFavorite };
  try {
    const updated = await prisma.dream.update({
      where: { id },
      data: { isFavorite }
    });
    return {
      ...updated,
      createdAt: updated.createdAt ? new Date(updated.createdAt).getTime() : Date.now()
    };
  } catch (e) {
    console.warn("Prisma toggleDreamFavorite error:", e.message);
    return { id, isFavorite };
  }
}

async function callGemini(prompt, apiKey) {
  const models = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-flash-latest"];
  let lastError = null;
  for (const model of models) {
    try {
      const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`;
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }],
          generationConfig: {
            responseMimeType: "application/json",
            temperature: 0.7
          }
        })
      });
      if (!response.ok) {
        const errText = await response.text();
        console.warn(`Model ${model} failed:`, errText);
        lastError = new Error(`Gemini (${model}): ${response.statusText}`);
        continue;
      }
      const data = await response.json();
      const jsonText = data.candidates?.[0]?.content?.parts?.[0]?.text;
      if (jsonText) {
        return JSON.parse(jsonText);
      }
    } catch (e) {
      lastError = e;
    }
  }
  throw lastError || new Error("Failed to generate content with Gemini API");
}

export async function extractDreamGraphAI(inputText, customApiKey = null) {
  const apiKey = customApiKey || process.env.GEMINI_API_KEY || process.env.NEXT_PUBLIC_GEMINI_API_KEY;
  if (!apiKey) {
    throw new Error("No Gemini API Key found. Please add GEMINI_API_KEY to your .env file.");
  }
  
  const prompt = `You are the Narrative Cortex, an AI dream archaeologist. Analyze the following dream memory and extract its dream graph entities and a thoughtful follow-up question.

Dream Memory:
"${inputText}"

Return ONLY a valid JSON object matching this exact schema:
{
  "nodes": [
    { "id": "n1", "type": "Character", "label": "Name of character/entity", "layer": "Conscious" },
    { "id": "n2", "type": "Location", "label": "Setting name", "layer": "Symbolic" },
    { "id": "n3", "type": "Totem", "label": "Key object/symbol", "layer": "Fear" },
    { "id": "n4", "type": "Emotion", "label": "Core feeling", "layer": "Subconscious" }
  ],
  "followUp": "A fascinating, psychological follow-up question asking about a gap or deeper emotion in this dream to inspire further storytelling."
}

Types must be one of: Character, Location, Totem, Emotion, Action.
Layers must be one of: Conscious, Memory, Symbolic, Fear, Subconscious.
Generate 4 to 8 nodes based on the dream.`;

  return await callGemini(prompt, apiKey);
}

export async function synthesizeScreenplayAI(inputText, followUpAnswer, lens, customApiKey = null) {
  const apiKey = customApiKey || process.env.GEMINI_API_KEY || process.env.NEXT_PUBLIC_GEMINI_API_KEY;
  if (!apiKey) {
    throw new Error("No Gemini API Key found. Please add GEMINI_API_KEY to your .env file.");
  }

  const prompt = `You are the Narrative Cortex, an expert screenwriter and cinematic sound designer. Adapt the following dream memory into a short cinematic screenplay script using a "${lens}" narrative lens.

Dream Memory: "${inputText}"
${followUpAnswer ? `Additional Dreamer Context: "${followUpAnswer}"` : ""}
Selected Narrative Lens: ${lens}

Return ONLY a valid JSON object matching this exact schema:
{
  "title": "A captivating cinematic title for this dream",
  "lens": "${lens}",
  "characters": [
    { "id": "char_1", "name": "Character Name", "role": "their role or archetype in the dream" },
    { "id": "char_2", "name": "Second Character", "role": "their role" }
  ],
  "scenes": [
    {
      "id": 1,
      "layer": "Subconscious Memory",
      "setting": "Detailed description of the scene setting and lighting",
      "emotional_tone": "The emotional atmosphere (e.g., uncanny, suspenseful, nostalgic)",
      "lines": [
        { "speaker": "Character Name or Narrator", "text": "Dramatic line of dialogue or internal narration revealing the dream's meaning." },
        { "speaker": "Second Character", "text": "Response or reaction." }
      ],
      "sound_cues": [
        { "type": "ambient", "prompt": "descriptive audio prompt for background sound (e.g. distant wind, humming wires)" },
        { "type": "one-shot", "prompt": "specific sound effect (e.g. glass shattering, footsteps echoing)", "position": "during line 1" },
        { "type": "music", "prompt": "musical score tone (e.g. low synth drone, cello crescendo)" }
      ]
    },
    {
      "id": 2,
      "layer": "Symbolic Truth",
      "setting": "Second setting or transformation of the dream space",
      "emotional_tone": "Climax or resolution tone",
      "lines": [
        { "speaker": "Character Name", "text": "Final climactic realization or line." }
      ],
      "sound_cues": [
        { "type": "music", "prompt": "swelling cinematic strings fading into silence" }
      ]
    }
  ]
}

Make the dialogue rich, atmospheric, and deeply tailored to the "${lens}" genre/lens. Create 2 to 3 vivid scenes. Ensure all JSON is perfectly formatted.`;

  return await callGemini(prompt, apiKey);
}