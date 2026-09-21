const { higgsfield } = require('@higgsfield/client/v2');

if (!process.env.HF_CREDENTIALS) {
  throw new Error(
    'HF_CREDENTIALS is not set. Copy .env.example to .env and add your KEY_ID:KEY_SECRET.'
  );
}

module.exports = { higgsfield };
