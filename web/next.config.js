/** @type {import('next').NextConfig} */
const nextConfig = {
	reactStrictMode: true,
	async redirects() {
		return [
			{
				source: '/strategies/swing-atr',
				destination: '/strategies/swing-perp-16h',
				permanent: false,
			},
		];
	},
};

module.exports = nextConfig;
