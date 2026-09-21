import { config as loadEnv } from 'dotenv';
loadEnv({ path: '.env.local' });

import { createHiggsfieldClient } from '@higgsfield/client/v2';

const MODEL_ENDPOINT = 'bytedance/seedance-2.5/text-to-video';

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
      duration: 5,
      resolution: '720p',
      aspect_ratio: '16:9',
    },
    withPolling: true,
  });

  const job = jobSet.jobs[0];

  if (jobSet.isCompleted && job?.results) {
    console.log('Video generated successfully.');
    console.log('Video URL:', job.results.raw.url);
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
  console.error('Seedance 2.5 generation did not succeed:', err instanceof Error ? err.message : err);
  process.exitCode = 1;
});
