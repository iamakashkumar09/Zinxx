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

// FastAPI backend (Zinxx/app.py) — the real dream pipeline (Modules 1->2->3->7) and
// audio production (Modules 8->9->10, real Qwen3-TTS voices + Stable Audio music/SFX).
// Not imported from lib/constants.js because that file is 'use client' and this one is
// 'use server' — kept as separate, identically-defaulted env reads instead.
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

async function backendFetch(path, body) {
  let res;
  try {
    res = await fetch(`${BACKEND_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  } catch (e) {
    throw new Error(`Could not reach backend at ${BACKEND_URL}${path} — is uvicorn running? (${e.message})`);
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Backend request to ${path} failed (${res.status})`);
  }
  return res.json();
}

/** Module 1 only — fast preview, used to populate the "Dream Graph" node visualization
 * shown during the studio's "extracting" step, before the full pipeline runs. */
export async function getStoryPreview(inputText) {
  const story = await backendFetch('/api/story', { text: inputText });

  const nodes = [];
  story.characters.forEach((c, i) => {
    nodes.push({ id: `char_${i}`, type: 'Character', label: c.name, layer: 'Conscious' });
  });
  const seenSettings = new Set();
  const seenTones = new Set();
  story.scenes.forEach((scene, i) => {
    if (scene.setting && !seenSettings.has(scene.setting)) {
      seenSettings.add(scene.setting);
      nodes.push({ id: `loc_${i}`, type: 'Location', label: scene.setting, layer: 'Symbolic' });
    }
    if (scene.emotional_tone && !seenTones.has(scene.emotional_tone)) {
      seenTones.add(scene.emotional_tone);
      nodes.push({ id: `emo_${i}`, type: 'Emotion', label: scene.emotional_tone, layer: 'Subconscious' });
    }
  });

  return {
    nodes,
    followUp: "Add any extra detail that could sharpen this reconstruction, or continue to synthesis as-is.",
  };
}

/** Full dream archaeology pipeline (Modules 1->2->3->7): text -> reconstructed screenplay
 * Story. The backend takes one text blob rather than a two-turn conversation, so a
 * follow-up answer (if the dreamer added one) is folded into the input text. */
export async function generateDreamStory(inputText, followUpAnswer, userId) {
  const text = followUpAnswer && followUpAnswer.trim()
    ? `${inputText}\n\nAdditional detail: ${followUpAnswer.trim()}`
    : inputText;
  const dreamResponse = await backendFetch('/api/dream', { text, user_id: userId });
  return dreamResponse.story;
}

/** Modules 8->9->10: emotion direction -> real Qwen3-TTS voices + Stable Audio music/SFX
 * -> final mixdown. Returns a relative audio_url served by the same FastAPI app. */
export async function generateAudio(story) {
  return await backendFetch('/api/audio', { story });
}