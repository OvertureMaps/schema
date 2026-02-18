import React, { useState, useMemo, useCallback } from 'react';
import '../css/taxonomyBrowser.css';

const SMALL_WORDS = new Set(['and', 'or', 'the', 'in', 'of', 'for', 'to', 'a', 'an']);

function toDisplayName(code) {
  if (!code) return '';
  return code.split('_').map((word, i) => {
    if (i > 0 && SMALL_WORDS.has(word)) return word;
    return word.charAt(0).toUpperCase() + word.slice(1);
  }).join(' ');
}

/**
 * Parse a single CSV line, handling quoted fields that contain commas.
 * Returns an array of field values.
 */
function parseCsvLine(line) {
  const fields = [];
  let i = 0;
  while (i <= line.length) {
    if (i === line.length) {
      fields.push('');
      break;
    }
    if (line[i] === '"') {
      let j = i + 1;
      let value = '';
      while (j < line.length) {
        if (line[j] === '"') {
          if (j + 1 < line.length && line[j + 1] === '"') {
            value += '"';
            j += 2;
          } else {
            j++;
            break;
          }
        } else {
          value += line[j];
          j++;
        }
      }
      fields.push(value);
      if (j < line.length && line[j] === ',') j++;
      i = j;
    } else {
      const commaIdx = line.indexOf(',', i);
      if (commaIdx === -1) {
        fields.push(line.slice(i));
        break;
      } else {
        fields.push(line.slice(i, commaIdx));
        i = commaIdx + 1;
      }
    }
  }
  return fields;
}

// ---------------------------------------------------------------------------
// Generic CSV parser
// ---------------------------------------------------------------------------

function parseCsv(csvText, fieldNames) {
  const lines = csvText.replace(/\r\n?/g, '\n').trim().split('\n');
  lines.shift();
  return lines
    .map(line => {
      const parts = parseCsvLine(line);
      if (!parts[0]) return null;
      const row = {};
      for (let i = 0; i < fieldNames.length; i++) {
        row[fieldNames[i]] = parts[i] || '';
      }
      return row;
    })
    .filter(Boolean);
}

function parseCountsCsv(csvText) {
  if (!csvText) return {};
  const lines = csvText.replace(/\r\n?/g, '\n').replace(/^\uFEFF/, '').trim().split('\n');
  lines.shift();
  const map = {};
  for (const line of lines) {
    const parts = parseCsvLine(line);
    const count = parseInt(parts[0], 10);
    const category = parts[1];
    if (category && !isNaN(count)) {
      map[category] = (map[category] || 0) + count;
    }
  }
  return map;
}

function parseCountsStats(csvText) {
  if (!csvText) return { totalPlaces: 0, uniqueCategories: 0, uniqueBasicCategories: 0 };
  const lines = csvText.replace(/\r\n?/g, '\n').replace(/^\uFEFF/, '').trim().split('\n');
  lines.shift();
  let totalPlaces = 0;
  const categories = new Set();
  const basicCategories = new Set();
  for (const line of lines) {
    const parts = parseCsvLine(line);
    const count = parseInt(parts[0], 10);
    if (!isNaN(count)) totalPlaces += count;
    if (parts[1]) categories.add(parts[1]);
    if (parts[2]) basicCategories.add(parts[2]);
  }
  return { totalPlaces, uniqueCategories: categories.size, uniqueBasicCategories: basicCategories.size };
}

function parseCountsCsvByBasic(csvText) {
  if (!csvText) return {};
  const lines = csvText.replace(/\r\n?/g, '\n').replace(/^\uFEFF/, '').trim().split('\n');
  lines.shift();
  const map = {};
  for (const line of lines) {
    const parts = parseCsvLine(line);
    const count = parseInt(parts[0], 10);
    const basicCategory = parts[2];
    if (basicCategory && !isNaN(count)) {
      map[basicCategory] = (map[basicCategory] || 0) + count;
    }
  }
  return map;
}

// ---------------------------------------------------------------------------
// Generic tree builder
// ---------------------------------------------------------------------------

function buildTree(rows, counts, config) {
  const nodeMap = {};

  if (config.hierarchyFields) {
    // Multi-field mode (April style): build path from multiple fields
    function ensureNode(hierarchy, displayName) {
      if (nodeMap[hierarchy]) return nodeMap[hierarchy];
      const node = {
        hierarchy,
        displayName,
        code: '',
        children: [],
        data: null,
        leafCount: null,
        totalCount: null,
      };
      nodeMap[hierarchy] = node;
      return node;
    }

    for (const row of rows) {
      const pathParts = [];
      for (const f of config.hierarchyFields) {
        const val = row[f];
        if (val) {
          // Skip duplicate when category === theme (original taxonomy quirk)
          if (pathParts.length > 0 && val === pathParts[pathParts.length - 1]) continue;
          pathParts.push(val);
        }
      }

      for (let i = 0; i < pathParts.length; i++) {
        const path = pathParts.slice(0, i + 1).join(' > ');
        const node = ensureNode(path, toDisplayName(pathParts[i]));
        node.code = pathParts[i];
      }

      const leafPath = pathParts.join(' > ');
      if (nodeMap[leafPath]) {
        nodeMap[leafPath].data = row;
        const c = counts[row[config.codeField]];
        if (c != null) {
          nodeMap[leafPath].leafCount = c;
          nodeMap[leafPath].totalCount = c;
        }
      }
    }
  } else {
    // Single-field mode (Oct/Dec style): split a pre-built hierarchy string
    function ensureNode(hierarchy) {
      if (nodeMap[hierarchy]) return nodeMap[hierarchy];
      const parts = hierarchy.split(' > ');
      const lastSegment = parts[parts.length - 1];
      const node = {
        hierarchy,
        displayName: toDisplayName(lastSegment),
        code: lastSegment,
        children: [],
        leafCount: null,
        totalCount: null,
      };
      nodeMap[hierarchy] = node;
      return node;
    }

    for (const row of rows) {
      const hierarchyValue = row[config.hierarchyField];
      if (!hierarchyValue) continue;
      const parts = hierarchyValue.split(' > ');
      for (let i = 0; i < parts.length; i++) {
        const path = parts.slice(0, i + 1).join(' > ');
        ensureNode(path);
      }

      const leafPath = hierarchyValue;
      const codeValue = row[config.codeField];
      if (nodeMap[leafPath] && codeValue) {
        nodeMap[leafPath].code = codeValue;
        const c = counts[codeValue];
        if (c != null) {
          nodeMap[leafPath].leafCount = c;
          nodeMap[leafPath].totalCount = c;
        }
      }
    }
  }

  // Build parent-child relationships
  const root = [];
  const paths = Object.keys(nodeMap).sort();
  for (const path of paths) {
    const node = nodeMap[path];
    const parts = path.split(' > ');
    if (parts.length === 1) {
      root.push(node);
    } else {
      const parentPath = parts.slice(0, -1).join(' > ');
      if (nodeMap[parentPath]) {
        if (!nodeMap[parentPath].children.find(c => c.hierarchy === path)) {
          nodeMap[parentPath].children.push(node);
        }
      }
    }
  }

  // Aggregate counts up the tree
  if (Object.keys(counts).length > 0) {
    function computeTotal(node) {
      if (node.children.length === 0) return node.leafCount || 0;
      let total = node.leafCount || 0;
      for (const child of node.children) {
        total += computeTotal(child);
      }
      node.totalCount = total;
      return total;
    }
    for (const node of root) computeTotal(node);
  }

  return { children: root, totalCategories: rows.length };
}

// ---------------------------------------------------------------------------
// Cross-tab lookup maps
// ---------------------------------------------------------------------------

function computePercentileTags(counts) {
  const entries = Object.entries(counts).filter(([, v]) => v != null && v > 0);
  if (entries.length === 0) return {};
  const sorted = entries.map(([, v]) => v).sort((a, b) => a - b);
  const tags = {};
  for (const [key, count] of entries) {
    const rank = sorted.filter(v => v < count).length;
    const pct = (rank / sorted.length) * 100;
    if (pct >= 99) tags[key] = 'Top 1%';
    else if (pct >= 90) tags[key] = 'Top 10%';
    else if (pct <= 1) tags[key] = 'Bottom 1%';
    else if (pct <= 10) tags[key] = 'Bottom 10%';
    else if (pct <= 25) tags[key] = 'Bottom 25%';
    else tags[key] = null;
  }
  return tags;
}

function buildLookups(releases, allRows, allCountsByPrimary, allCountsByBasic) {
  const lookups = {};
  for (let i = 0; i < releases.length; i++) {
    const cfg = releases[i];
    const rows = allRows[cfg.id];
    const counts = allCountsByPrimary[cfg.id];
    const basicCounts = allCountsByBasic[cfg.id];
    const prevBasicCounts = i > 0 ? allCountsByBasic[releases[i - 1].id] : null;
    const pctTags = computePercentileTags(counts);

    // Determine which release's counts to use for prevCount based on matchType
    let prevCountSource = null;
    if (cfg.matchType === 'original') {
      prevCountSource = allCountsByPrimary[releases[0].id];
    } else if (cfg.matchType === 'new' && i > 0) {
      prevCountSource = allCountsByPrimary[releases[i - 1].id];
    } else if (i > 0) {
      prevCountSource = allCountsByPrimary[releases[i - 1].id];
    }

    lookups[cfg.id] = {};
    for (const row of rows) {
      const code = row[cfg.codeField];
      if (!code || lookups[cfg.id][code]) continue;

      const hierarchy = cfg.hierarchyField
        ? row[cfg.hierarchyField]
        : cfg.hierarchyFields.filter(f => row[f]).map(f => row[f]).join(' > ');

      const basicLabel = cfg.basicCategoryField ? row[cfg.basicCategoryField] : null;

      // Use matchColumn for prevCount lookup when available, otherwise fall back to code
      const matchCode = cfg.matchColumn ? row[cfg.matchColumn] : null;
      let prevCount = null;
      if (prevCountSource) {
        if (matchCode) {
          prevCount = prevCountSource[matchCode] ?? null;
        } else {
          prevCount = prevCountSource[code] ?? null;
        }
      }

      const entry = {
        ...row,
        hierarchy,
        code,
        basicCategory: basicLabel,
        count: counts[code] ?? null,
        prevCount,
        basicCount: basicLabel && basicCounts ? (basicCounts[basicLabel] ?? null) : null,
        prevBasicCount: basicLabel && prevBasicCounts ? (prevBasicCounts[basicLabel] ?? null) : null,
        pctTag: pctTags[code] || null,
      };

      lookups[cfg.id][code] = entry;

      // Also index by matchColumn value for cross-tab lookups
      if (matchCode && matchCode !== code && !lookups[cfg.id][matchCode]) {
        lookups[cfg.id][matchCode] = entry;
      }
    }
  }
  return lookups;
}

// ---------------------------------------------------------------------------
// Shared components
// ---------------------------------------------------------------------------

function TreeNode({ node, depth, expanded, onToggle, selected, onSelect }) {
  const hasChildren = node.children.length > 0;
  const isExpanded = expanded.has(node.hierarchy);
  const isSelected = selected && selected.hierarchy === node.hierarchy;

  let className = 'taxonomy-tree-item';
  if (isSelected) className += ' taxonomy-tree-item--selected';

  return (
    <div>
      <div
        className={className}
        style={{ paddingLeft: `${depth * 20 + 12}px` }}
        onClick={() => {
          onSelect(node);
          if (hasChildren) onToggle(node.hierarchy);
        }}
      >
        <span className="taxonomy-tree-chevron">
          {hasChildren ? (isExpanded ? '▾' : '▸') : '·'}
        </span>
        <span className="taxonomy-tree-name">{node.displayName}</span>
        {node.totalCount != null && (
          <span className="taxonomy-tree-count">
            {node.totalCount.toLocaleString()}
          </span>
        )}
      </div>
      {hasChildren && isExpanded && (
        <div>
          {node.children.map(child => (
            <TreeNode
              key={child.hierarchy}
              node={child}
              depth={depth + 1}
              expanded={expanded}
              onToggle={onToggle}
              selected={selected}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function Breadcrumb({ hierarchy }) {
  if (!hierarchy) return null;
  const parts = hierarchy.split(' > ').map(p => p.replace(/_/g, ' '));
  return (
    <div className="taxonomy-detail-breadcrumb">
      {parts.map((part, i) => (
        <span key={i}>
          {i > 0 && <span className="taxonomy-detail-arrow"> &#x203A; </span>}
          <span className="taxonomy-detail-crumb">{part}</span>
        </span>
      ))}
    </div>
  );
}

function CollapsibleSection({ title, defaultOpen, noMatch, note, children }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="taxonomy-collapsible">
      <button
        className={`taxonomy-collapsible-header ${open ? 'taxonomy-collapsible-header--open' : ''}`}
        onClick={noMatch ? undefined : () => setOpen(!open)}
        style={noMatch ? { cursor: 'default' } : undefined}
      >
        <span className="taxonomy-collapsible-chevron">{noMatch ? '·' : (open ? '▾' : '▸')}</span>
        <span>{title}</span>
        {noMatch && <span className="taxonomy-no-match-tag">No Match</span>}
      </button>
      {!noMatch && open && (
        <div className="taxonomy-collapsible-content">
          {note && <p className="taxonomy-section-note">{note}</p>}
          {children}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section content renderer
// ---------------------------------------------------------------------------

function pctTagClass(tag) {
  if (!tag) return '';
  if (tag.startsWith('Top')) return 'taxonomy-pct-top';
  if (tag.startsWith('Bottom')) return 'taxonomy-pct-bottom';
  return '';
}

function PctTag({ tag }) {
  if (!tag) return null;
  return <span className={`taxonomy-pct-tag ${pctTagClass(tag)}`}>{tag}</span>;
}

function ChangeIndicator({ current, previous }) {
  if (previous == null || current == null) return null;
  if (previous === 0 && current === 0) return null;
  if (previous === 0) {
    return <span className="taxonomy-change-up"> (new)</span>;
  }
  const pctRaw = ((current - previous) / previous) * 100;
  const pct = Math.abs(pctRaw) >= 1 ? Math.round(pctRaw) : Math.round(pctRaw * 10) / 10;
  if (pct === 0) return null;
  const isUp = pct > 0;
  return (
    <span className={isUp ? 'taxonomy-change-up' : 'taxonomy-change-down'}>
      {' '}({isUp ? '↑' : '↓'} {Math.abs(pct)}%)
    </span>
  );
}

function HierarchyLevelList({ hierarchy, selectedCode, basicCategory, basicCount, prevBasicCount, count, prevCount, pctTag, mappings, displayFields, data }) {
  if (!hierarchy) return null;
  const parts = hierarchy.split(' > ');
  const items = parts.map((part, i) => ({
    label: `Level ${i}`,
    value: part.replace(/_/g, ' '),
    selected: part.trim() === selectedCode,
  }));
  if (basicCategory) {
    items.push({ label: 'Basic Category', value: basicCategory.replace(/_/g, ' ') });
  }
  if (displayFields && data) {
    for (const df of displayFields) {
      const val = data[df.field];
      if (val) {
        items.push({ label: df.label, value: String(val).replace(/_/g, ' ') });
      }
    }
  }
  if (basicCount != null) {
    items.push({ label: 'Basic Count', value: basicCount.toLocaleString(), countChange: { current: basicCount, previous: prevBasicCount } });
  }
  if (count != null) {
    items.push({ label: 'Count', value: count.toLocaleString(), countChange: { current: count, previous: prevCount } });
  }
  if (pctTag) {
    items.push({ label: 'Note', value: pctTag, isPctTag: true });
  }
  if (mappings && mappings.length > 0) {
    mappings.forEach((m) => {
      items.push({
        label: m.match_type,
        value: m.overture_label.replace(/_/g, ' '),
      });
    });
  }
  return (
    <div className="taxonomy-kv-list">
      {items.map((item, i) => (
        <div key={i} className="taxonomy-kv-item">
          <span className="taxonomy-kv-label">{item.label}</span>
          {item.isPctTag ? (
            <PctTag tag={item.value} />
          ) : (
            <span className={item.selected ? 'taxonomy-kv-value taxonomy-kv-value--selected' : 'taxonomy-kv-value'}>
              {item.value}
              {item.countChange && <ChangeIndicator current={item.countChange.current} previous={item.countChange.previous} />}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

function SectionContent({ data, release }) {
  return (
    <div className="taxonomy-section-body">
      <HierarchyLevelList
        hierarchy={data.hierarchy}
        selectedCode={data.code}
        basicCategory={data.basicCategory}
        basicCount={data.basicCount}
        prevBasicCount={data.prevBasicCount}
        count={data.count}
        prevCount={data.prevCount}
        pctTag={data.pctTag}
        displayFields={release.displayFields}
        data={data}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Detail panel with cross-tab collapsible sections
// ---------------------------------------------------------------------------

function DetailPanel({ node, activeTab, lookups, releases }) {
  if (!node) {
    return (
      <div className="taxonomy-detail-empty">
        <h3>Select a category from the tree</h3>
        <p>Navigate the taxonomy hierarchy on the left to view detailed category data</p>
      </div>
    );
  }

  const code = node.code;

  return (
    <div className="taxonomy-detail" key={node.hierarchy}>
      <h2 className="taxonomy-detail-name">{node.displayName}</h2>
      <div className="taxonomy-detail-sections">
        {releases.map(release => {
          const data = lookups[release.id]?.[code] || null;
          return (
            <CollapsibleSection
              key={release.id}
              title={release.label}
              defaultOpen={activeTab === release.id}
              noMatch={!data}
              note={release.note}
            >
              {data && <SectionContent data={data} release={release} />}
            </CollapsibleSection>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function TaxonomyBrowser({ releases: allReleases }) {
  // Filter to only enabled releases
  const releases = useMemo(
    () => allReleases.filter(r => r.enabled !== false),
    [allReleases]
  );

  const [activeTab, setActiveTab] = useState(releases[0]?.id || '');
  const [searchTerm, setSearchTerm] = useState('');
  const [expanded, setExpanded] = useState(new Set());
  const [selected, setSelected] = useState(null);

  // Parse all data CSVs
  const allRows = useMemo(() => {
    const result = {};
    for (const r of releases) {
      result[r.id] = parseCsv(r.dataCsv, r.fieldNames);
    }
    return result;
  }, [releases]);

  // Parse all counts (by primary category)
  const allCountsByPrimary = useMemo(() => {
    const result = {};
    for (const r of releases) {
      result[r.id] = parseCountsCsv(r.countsCsv);
    }
    return result;
  }, [releases]);

  // Parse all counts (by basic category)
  const allCountsByBasic = useMemo(() => {
    const result = {};
    for (const r of releases) {
      result[r.id] = parseCountsCsvByBasic(r.countsCsv);
    }
    return result;
  }, [releases]);

  // Build all trees
  const allTrees = useMemo(() => {
    const result = {};
    for (const r of releases) {
      result[r.id] = buildTree(allRows[r.id], allCountsByPrimary[r.id], r);
    }
    return result;
  }, [releases, allRows, allCountsByPrimary]);

  // Build lookups
  const lookups = useMemo(
    () => buildLookups(releases, allRows, allCountsByPrimary, allCountsByBasic),
    [releases, allRows, allCountsByPrimary, allCountsByBasic]
  );

  // Stats per release
  const releaseStats = useMemo(() => {
    const result = {};
    for (const r of releases) {
      result[r.id] = parseCountsStats(r.countsCsv);
    }
    return result;
  }, [releases]);

  // Previous release stats (for change indicators)
  const prevReleaseStats = useMemo(() => {
    const result = {};
    for (let i = 0; i < releases.length; i++) {
      result[releases[i].id] = i > 0 ? releaseStats[releases[i - 1].id] : null;
    }
    return result;
  }, [releases, releaseStats]);

  // Current tree based on activeTab
  const tree = allTrees[activeTab] || { children: [], totalCategories: 0 };

  const handleTabChange = useCallback((tab) => {
    setActiveTab(tab);
    setSelected(null);
    setExpanded(new Set());
    setSearchTerm('');
  }, []);

  const handleToggle = useCallback((hierarchy) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(hierarchy)) {
        next.delete(hierarchy);
      } else {
        next.add(hierarchy);
      }
      return next;
    });
  }, []);

  const handleSelect = useCallback((node) => {
    setSelected(node);
  }, []);

  const filteredTree = useMemo(() => {
    if (!searchTerm) return tree.children;

    function filterNode(node) {
      const term = searchTerm.toLowerCase();
      const matches = node.displayName.toLowerCase().includes(term) ||
                      node.code.toLowerCase().includes(term);

      const filteredChildren = node.children
        .map(filterNode)
        .filter(Boolean);

      if (matches || filteredChildren.length > 0) {
        return { ...node, children: filteredChildren };
      }
      return null;
    }

    return tree.children.map(filterNode).filter(Boolean);
  }, [tree, searchTerm]);

  const effectiveExpanded = useMemo(() => {
    if (!searchTerm) return expanded;
    const autoExpanded = new Set(expanded);

    function expandMatching(node) {
      const term = searchTerm.toLowerCase();
      const matches = node.displayName.toLowerCase().includes(term) ||
                      node.code.toLowerCase().includes(term);
      let childMatches = false;
      for (const child of node.children) {
        if (expandMatching(child)) childMatches = true;
      }
      if (childMatches) {
        autoExpanded.add(node.hierarchy);
      }
      return matches || childMatches;
    }

    for (const node of tree.children) {
      expandMatching(node);
    }
    return autoExpanded;
  }, [expanded, searchTerm, tree]);

  return (
    <div className="taxonomy-browser">
      <div className="taxonomy-browser-left">
        <div className="taxonomy-browser-header">
          <span className="taxonomy-browser-header-label">Choose a release:</span>
          <select
            className="taxonomy-browser-select"
            value={activeTab}
            onChange={e => handleTabChange(e.target.value)}
          >
            {releases.map(r => (
              <option key={r.id} value={r.id}>{r.label}</option>
            ))}
          </select>
        </div>
        {(() => {
          const cfg = releases.find(r => r.id === activeTab);
          const tags = cfg?.tags || [];
          const releaseUrl = cfg?.releaseUrl || '';
          const stats = releaseStats[activeTab];
          const prevStats = prevReleaseStats[activeTab];
          return (
            <div className="taxonomy-info-rows">
              <div className="taxonomy-info-row">
                {tags.map((tag, i) => (
                  <div key={i} className="taxonomy-info-cell">
                    <div className="taxonomy-info-label">{tag.title === 'Date' ? 'Release Date' : tag.title}</div>
                    <div className="taxonomy-info-value">
                      {tag.title === 'Date' && releaseUrl ? (
                        <a href={releaseUrl} target="_blank" rel="noopener noreferrer">{tag.label}</a>
                      ) : tag.label}
                    </div>
                  </div>
                ))}
              </div>
              {stats && stats.totalPlaces > 0 ? (
                <div className="taxonomy-info-row">
                  <div className="taxonomy-info-cell">
                    <div className="taxonomy-info-label">Total Places</div>
                    <div className="taxonomy-info-value">
                      {stats.totalPlaces.toLocaleString()}
                      <ChangeIndicator current={stats.totalPlaces} previous={prevStats?.totalPlaces} />
                    </div>
                  </div>
                  <div className="taxonomy-info-cell">
                    <div className="taxonomy-info-label">Unique Categories</div>
                    <div className="taxonomy-info-value">
                      {stats.uniqueCategories.toLocaleString()}
                      <ChangeIndicator current={stats.uniqueCategories} previous={prevStats?.uniqueCategories} />
                    </div>
                  </div>
                  <div className="taxonomy-info-cell">
                    <div className="taxonomy-info-label">Basic Categories</div>
                    <div className="taxonomy-info-value">
                      {stats.uniqueBasicCategories.toLocaleString()}
                      <ChangeIndicator current={stats.uniqueBasicCategories} previous={prevStats?.uniqueBasicCategories} />
                    </div>
                  </div>
                </div>
              ) : (
                <div className="taxonomy-info-row">
                  <div className="taxonomy-info-cell">
                    <div className="taxonomy-info-label">Counts</div>
                    <div className="taxonomy-info-value">No Data</div>
                  </div>
                </div>
              )}
            </div>
          );
        })()}
        <input
          type="text"
          className="taxonomy-browser-search"
          placeholder="Search categories..."
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
        />
        <div className="taxonomy-browser-tree">
          {filteredTree.map(node => (
            <TreeNode
              key={node.hierarchy}
              node={node}
              depth={0}
              expanded={effectiveExpanded}
              onToggle={handleToggle}
              selected={selected}
              onSelect={handleSelect}
            />
          ))}
          {filteredTree.length === 0 && (
            <div className="taxonomy-tree-empty">No categories match your search.</div>
          )}
        </div>
      </div>
      <div className="taxonomy-browser-right">
        <DetailPanel node={selected} activeTab={activeTab} lookups={lookups} releases={releases} />
      </div>
    </div>
  );
}
