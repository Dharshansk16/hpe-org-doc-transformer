const { buildNormalizedEvent } = require("../schema");

module.exports = function normalizeConfluence({ payload, fullData }) {

  return buildNormalizedEvent({
    doc_id: String(fullData.pageId),

    source: "confluence",

    title: fullData.title,

    content: fullData.content,

    metadata: {
      version: fullData.version,
      eventType: fullData.eventType,
      space: fullData.space,
      url: fullData.url,

      updatedBy: {
        accountId: fullData.updatedBy?.accountId || null,
        displayName: fullData.updatedBy?.displayName || null,
      },

      change: {
        versionBefore: fullData.change?.versionBefore || null,
        versionAfter: fullData.change?.versionAfter || null,
      },

      timestamp: payload.timestamp || null,
    },
  });
};