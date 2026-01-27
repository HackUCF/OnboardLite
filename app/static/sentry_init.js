document.addEventListener("DOMContentLoaded", function () {
  const dsnMeta = document.querySelector('meta[name="sentry-dsn"]');
  if (dsnMeta && typeof Sentry !== "undefined") {
    Sentry.init({
      dsn: dsnMeta.content,
      tracesSampleRate: 0.01,
    });
  }
});
