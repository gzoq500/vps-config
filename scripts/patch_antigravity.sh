#!/bin/bash
# Auto-patch 9Router Antigravity after install/update
# Fixes: User-Agent (Trae) + Google Search Grounding

NRDIR="/usr/local/lib/node_modules/9router"
PATCHED=0

# Patch User-Agent in all antigravity chunks
for f in "$NRDIR"/app/.next-cli-build/server/chunks/*.js; do
    [ -f "$f" ] || continue
    if grep -q 'antigravity' "$f" 2>/dev/null; then
        if grep -q 'antigravity/ide/' "$f" 2>/dev/null; then
            sed -i 's|antigravity/ide/${m} darwin/arm64|Trae/1.0.0 antigravity-cockpit-tools|g' "$f"
            PATCHED=$((PATCHED + 1))
        fi
        if grep -q '"User-Agent":f}' "$f" 2>/dev/null; then
            sed -i 's|"User-Agent":f}|"User-Agent":"Trae/1.0.0 antigravity-cockpit-tools"}|g' "$f"
            PATCHED=$((PATCHED + 1))
        fi
        if grep -q '"User-Agent":g}' "$f" 2>/dev/null; then
            sed -i 's|"User-Agent":g}|"User-Agent":"Trae/1.0.0 antigravity-cockpit-tools"}|g' "$f"
            PATCHED=$((PATCHED + 1))
        fi
    fi
done

# Patch Google Search grounding
for f in "$NRDIR"/app/.next-cli-build/server/chunks/*.js; do
    [ -f "$f" ] || continue
    if grep -q 'toolNameMap:null}' "$f" 2>/dev/null; then
        if ! grep -q 'google_search' "$f" 2>/dev/null; then
            sed -i 's|cloakedBody:a,toolNameMap:null}|cloakedBody:a,toolNameMap:null};if(!a.request)a.request={};if(!a.request.tools)a.request.tools=[];a.request.tools.push({google_search:{}});|g' "$f"
            PATCHED=$((PATCHED + 1))
        fi
    fi
done

echo "Patched $PATCHED locations"
