import { config as loadEnv } from 'dotenv';
loadEnv({ path: '.env.local' });

import { createHiggsfieldClient } from '@higgsfield/client/v2';

const MODEL_ENDPOINT = 'flux-pro/kontext/max/text-to-image';

async function main(): Promise<void> {
  if (!process.env.HF_CREDENTIALS) {
    throw new Error(
      'HF_CREDENTIALS is not set in .env.local. Add it in key-id:key-secret format.'
    );
  }

  const client = createHiggsfieldClient({
    credentials: process.env.HF_CREDENTIALS,
  });

  const jobSet = await client.subscribe(MODEL_ENDPOINT, {
    input: {
      prompt: 'A cinematic scene at sunset',
      aspect_ratio: '16:9',
      safety_tolerance: 2,
    },
    withPolling: true,
  });

  const job = jobSet.jobs[0];

  if (jobSet.isCompleted && job?.results) {
    console.log('Image generated successfully.');
    console.log('Image URL:', job.results.raw.url);
    return;
  }

  if (jobSet.isNsfw || job?.status === 'nsfw') {
    throw new Error('Request was rejected by content moderation (NSFW).');
  }

  if (jobSet.isFailed || job?.status === 'failed') {
    throw new Error('Generation failed on the Higgsfield backend.');
  }

  if (job?.status === 'canceled') {
    throw new Error('Generation was canceled before completion.');
  }

  throw new Error(`Generation did not complete. Final status: ${job?.status ?? 'unknown'}`);
}

main().catch((err) => {
  console.error('Image generation did not succeed:', err instanceof Error ? err.message : err);
  process.exitCode = 1;
});
