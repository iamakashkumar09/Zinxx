'use server'

import { prisma } from '@/lib/prisma'

export async function loginUser(email, password) {
  const user = await prisma.user.findUnique({ where: { email } });
  if (!user || user.password !== password) throw new Error("Invalid credentials");
  return { id: user.id, email: user.email, name: user.name };
}

export async function registerUser(email, password, name) {
  const existing = await prisma.user.findUnique({ where: { email } });
  if (existing) throw new Error("Email already exists");
  const user = await prisma.user.create({ data: { email, password, name } });
  return { id: user.id, email: user.email, name: user.name };
}

export async function saveDream(userId, inputText, storyData, lens) {
  return await prisma.dream.create({
    data: { userId, inputText, storyData, lens }
  });
}

export async function getDreams(userId) {
  return await prisma.dream.findMany({
    where: { userId },
    orderBy: { createdAt: 'desc' }
  });
}

export async function deleteDream(id) {
  return await prisma.dream.delete({ where: { id } });
}