import { PrismaClient } from '@prisma/client'
import { PrismaNeon } from '@prisma/adapter-neon'
import { neonConfig } from '@neondatabase/serverless'
import ws from 'ws'

neonConfig.webSocketConstructor = ws;

const createPrismaClient = () => {
  if (!process.env.DATABASE_URL) {
    return null;
  }
  try {
    const adapter = new PrismaNeon({ connectionString: process.env.DATABASE_URL });
    return new PrismaClient({ adapter });
  } catch (e) {
    console.warn("Failed to initialize PrismaClient:", e.message);
    return null;
  }
};

export const prisma = global.prisma || createPrismaClient();

if (process.env.NODE_ENV !== 'production' && prisma) {
  global.prisma = prisma;
}