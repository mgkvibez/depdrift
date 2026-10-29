"""Bundled list of popular package names used for typosquat distance checks.

Kept in the repo so the tool stays local: no registry calls, no API key.
"""

from __future__ import annotations

POPULAR: tuple[str, ...] = (
    "react", "react-dom", "next", "vue", "svelte", "angular", "express", "koa", "fastify",
    "lodash", "underscore", "axios", "node-fetch", "got", "request", "chalk", "commander",
    "yargs", "debug", "dotenv", "uuid", "nanoid", "moment", "dayjs", "date-fns", "zod",
    "joi", "ajv", "yup", "typescript", "ts-node", "tslib", "eslint", "prettier", "jest",
    "mocha", "chai", "vitest", "playwright", "puppeteer", "cypress", "webpack", "rollup",
    "vite", "esbuild", "babel-core", "postcss", "tailwindcss", "sass", "less", "styled-components",
    "mongoose", "sequelize", "prisma", "knex", "pg", "mysql", "mysql2", "redis", "ioredis",
    "jsonwebtoken", "bcrypt", "bcryptjs", "passport", "helmet", "cors", "body-parser",
    "socket.io", "ws", "graphql", "apollo-server", "react-query", "redux", "zustand", "mobx",
    "formik", "react-hook-form", "framer-motion", "d3", "chart.js", "three", "sharp",
    "jimp", "cheerio", "jsdom", "puppeteer-core", "nodemon", "pm2", "concurrently", "rimraf",
    "glob", "minimatch", "semver", "chokidar", "fs-extra", "mkdirp", "cross-env", "dotenv-expand",
    "clsx", "classnames", "immer", "rxjs", "lodash-es", "core-js", "regenerator-runtime",
    "node-sass", "electron", "tauri", "expo", "react-native", "capacitor", "ionic",
    "openai", "anthropic", "langchain", "pinecone", "stripe", "twilio", "sendgrid",
    "passport-jwt", "express-session", "cookie-parser", "multer", "morgan", "winston", "pino",
)
