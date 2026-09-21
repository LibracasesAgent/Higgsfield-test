require('dotenv').config();
const { higgsfield } = require('./client');

async function main() {
  const jobSet = await higgsfield.subscribe('flux-pro/kontext/max/text-to-image', {
    input: {
      aspect_ratio: '1:1',
      prompt: 'A tiny test image to confirm the Higgsfield API connection works',
      safety_tolerance: 2,
    },
    withPolling: true,
  });

  if (jobSet.isCompleted) {
    console.log('Connection OK. Image URL:', jobSet.jobs[0].results?.raw.url);
  } else {
    console.log('Job did not complete. Status:', jobSet.jobs[0]?.status);
  }
}

main().catch((err) => {
  console.error('Connection test failed:', err.message);
  process.exit(1);
});
