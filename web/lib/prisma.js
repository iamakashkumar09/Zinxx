import { PrismaClient } from '@prisma/client'

const createPrismaClient = () => {
  if (!process.env.DATABASE_URL) {
    return null;
  }
  try {
    return new PrismaClient();
  } catch (e) {
    console.warn("Failed to initialize PrismaClient:", e.message);
    return null;
  }
};

export const prisma = global.prisma || createPrismaClient();

if (process.env.NODE_ENV !== 'production' && prisma) {
  global.prisma = prisma;
}