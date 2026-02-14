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

function parseCsv(csvText) {
  const lines = csvText.trim().split('\n');
  lines.shift();
  return lines
    .map(line => {
      const parts = line.split(',');
      if (!parts[4]) return null;
      return {
        group: parts[0],
        level: parseInt(parts[1]),
        isBasic: parts[2] === 'TRUE',
        hierarchy: parts[3],
        primaryCategory: parts[4],
        displayName: parts[5],
        basicCategory: parts[6] || '',
        oldHierarchy: parts[7] || '',
        oldPrimaryCategory: parts[8] || '',
        added: parts[9] === 'TRUE',
        renamed: parts[10] === 'TRUE',
        removed: parts[11] === 'TRUE',
        redirectTo: parts[12] || '',
      };
    })
    .filter(Boolean);
}

function buildNewTree(categories, counts) {
  const root = [];
  const nodeMap = {};

  for (const cat of categories) {
    const leafCount = counts ? (counts[cat.primaryCategory] || 0) : null;

    const node = {
      code: cat.primaryCategory,
      displayName: cat.displayName,
      level: cat.level,
      isBasic: cat.isBasic,
      basicCategory: cat.basicCategory,
      hierarchy: cat.hierarchy,
      oldHierarchy: cat.oldHierarchy,
      oldPrimaryCategory: cat.oldPrimaryCategory,
      added: cat.added,
      renamed: cat.renamed,
      removed: cat.removed,
      redirectTo: cat.redirectTo,
      children: [],
      leafCount: leafCount,
      totalCount: leafCount,
    };

    nodeMap[cat.hierarchy] = node;

    const pathParts = cat.hierarchy.split(' > ');
    if (pathParts.length === 1) {
      root.push(node);
    } else {
      const parentPath = pathParts.slice(0, -1).join(' > ');
      if (nodeMap[parentPath]) {
        nodeMap[parentPath].children.push(node);
      }
    }
  }

  if (counts) {
    function computeTotalCount(node) {
      if (node.children.length === 0) return node.leafCount || 0;
      let total = node.leafCount || 0;
      for (const child of node.children) {
        total += computeTotalCount(child);
      }
      node.totalCount = total;
      return total;
    }
    for (const node of root) computeTotalCount(node);
  }

  return { children: root, totalCategories: categories.length };
}

function buildOldTree(categories) {
  const nodeMap = {};
  const validCategories = categories.filter(cat => cat.oldHierarchy);

  // First pass: create all nodes including intermediates
  for (const cat of validCategories) {
    const pathParts = cat.oldHierarchy.split(' > ');

    for (let i = 0; i < pathParts.length; i++) {
      const path = pathParts.slice(0, i + 1).join(' > ');
      if (!nodeMap[path]) {
        nodeMap[path] = {
          code: pathParts[i],
          displayName: toDisplayName(pathParts[i]),
          level: i,
          isBasic: false,
          basicCategory: '',
          hierarchy: path,
          newHierarchy: '',
          newPrimaryCategory: '',
          newDisplayName: '',
          renamed: false,
          removed: false,
          added: false,
          children: [],
          totalCount: null,
          leafCount: null,
        };
      }
    }

    // Update leaf node with cross-reference data
    const leafNode = nodeMap[cat.oldHierarchy];
    leafNode.code = cat.oldPrimaryCategory;
    leafNode.displayName = toDisplayName(cat.oldPrimaryCategory);
    leafNode.level = pathParts.length - 1;
    leafNode.basicCategory = cat.basicCategory;
    leafNode.isBasic = cat.isBasic;
    leafNode.newHierarchy = cat.hierarchy;
    leafNode.newPrimaryCategory = cat.primaryCategory;
    leafNode.newDisplayName = cat.displayName;
    leafNode.renamed = cat.renamed;
    leafNode.removed = cat.removed;
  }

  // Second pass: link children to parents
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

  return { children: root, totalCategories: validCategories.length };
}

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
        {node.totalCount !== null && (
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

function DetailPanel({ node, totalPois, activeTab }) {
  if (!node) {
    return (
      <div className="taxonomy-detail-empty">
        <h3>Select a category from the tree</h3>
        <p>Navigate the taxonomy hierarchy on the left to view detailed category data</p>
      </div>
    );
  }

  const percentage = totalPois && node.totalCount
    ? ((node.totalCount / totalPois) * 100).toFixed(2)
    : null;

  const isNewTab = activeTab === 'new';

  return (
    <div className="taxonomy-detail">
      <Breadcrumb hierarchy={node.hierarchy} />
      <h2 className="taxonomy-detail-name">{node.displayName}</h2>

      <div className="taxonomy-detail-meta">
        <span className="taxonomy-detail-level">Level {node.level}</span>
        {node.basicCategory && (
          <span className="taxonomy-detail-basic-inline">
            Basic Category: <code>{node.basicCategory}</code>
          </span>
        )}
        {node.isBasic && (
          <span className="taxonomy-detail-badge">Basic Category</span>
        )}
      </div>

      {node.totalCount !== null && (
        <div className="taxonomy-detail-poi-row">
          <strong>{node.totalCount.toLocaleString()}</strong> POIs
          {percentage !== null && (
            <span className="taxonomy-detail-pct"> ({percentage}% of all POIs)</span>
          )}
        </div>
      )}

      <div className="taxonomy-detail-crossref">
        {isNewTab ? (
          <>
            <h4>{node.oldHierarchy ? 'Old Taxonomy' : 'No Old Taxonomy'}</h4>
            {node.oldHierarchy ? (
              <>
                <div className="taxonomy-detail-crossref-row">
                  <span className="taxonomy-detail-crossref-label">Old Hierarchy:</span>
                  <Breadcrumb hierarchy={node.oldHierarchy} />
                </div>
                <div className="taxonomy-detail-crossref-row">
                  <span className="taxonomy-detail-crossref-label">Old Primary:</span>
                  <code>{node.oldPrimaryCategory}</code>
                </div>
              </>
            ) : (
              <p className="taxonomy-detail-crossref-note">This category was added in the new taxonomy.</p>
            )}
            {node.removed && node.redirectTo && (
              <div className="taxonomy-detail-crossref-row">
                <span className="taxonomy-detail-crossref-label">Status:</span>
                <span>Removed — redirects to <code>{node.redirectTo}</code></span>
              </div>
            )}
            {node.renamed && (
              <div className="taxonomy-detail-crossref-row">
                <span className="taxonomy-detail-crossref-label">Status:</span>
                <span>Renamed from <code>{node.oldPrimaryCategory}</code></span>
              </div>
            )}
            {node.added && (
              <div className="taxonomy-detail-crossref-row">
                <span className="taxonomy-detail-crossref-label">Status:</span>
                <span>New category</span>
              </div>
            )}
          </>
        ) : (
          <>
            <h4>{node.newHierarchy ? 'New Taxonomy' : 'No New Taxonomy'}</h4>
            {node.newHierarchy ? (
              <>
                <div className="taxonomy-detail-crossref-row">
                  <span className="taxonomy-detail-crossref-label">New Hierarchy:</span>
                  <Breadcrumb hierarchy={node.newHierarchy} />
                </div>
                <div className="taxonomy-detail-crossref-row">
                  <span className="taxonomy-detail-crossref-label">New Primary:</span>
                  <code>{node.newPrimaryCategory}</code>
                </div>
                {node.newDisplayName && (
                  <div className="taxonomy-detail-crossref-row">
                    <span className="taxonomy-detail-crossref-label">New Display Name:</span>
                    <span>{node.newDisplayName}</span>
                  </div>
                )}
              </>
            ) : (
              <p className="taxonomy-detail-crossref-note">Structural node in the old taxonomy.</p>
            )}
            {node.removed && (
              <div className="taxonomy-detail-crossref-row">
                <span className="taxonomy-detail-crossref-label">Status:</span>
                <span>Removed</span>
              </div>
            )}
            {node.renamed && (
              <div className="taxonomy-detail-crossref-row">
                <span className="taxonomy-detail-crossref-label">Status:</span>
                <span>Renamed to <code>{node.newPrimaryCategory}</code></span>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default function TaxonomyBrowser({ csvData, countsData }) {
  const [activeTab, setActiveTab] = useState('new');
  const [searchTerm, setSearchTerm] = useState('');
  const [expanded, setExpanded] = useState(new Set());
  const [selected, setSelected] = useState(null);

  const categories = useMemo(() => parseCsv(csvData), [csvData]);

  const counts = useMemo(() => {
    if (!countsData) return null;
    try {
      const data = JSON.parse(countsData);
      const map = {};
      for (const item of data) {
        map[item.category] = item.count;
      }
      return map;
    } catch {
      return null;
    }
  }, [countsData]);

  const newTree = useMemo(() => buildNewTree(categories, counts), [categories, counts]);
  const oldTree = useMemo(() => buildOldTree(categories), [categories]);

  const tree = activeTab === 'new' ? newTree : oldTree;

  const totalPois = useMemo(() => {
    if (!counts) return null;
    return Object.values(counts).reduce((sum, c) => sum + c, 0);
  }, [counts]);

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
          <div className="taxonomy-browser-tabs">
            <button
              className={`taxonomy-tab ${activeTab === 'new' ? 'taxonomy-tab--active' : ''}`}
              onClick={() => handleTabChange('new')}
            >
              New Taxonomy
            </button>
            <button
              className={`taxonomy-tab ${activeTab === 'old' ? 'taxonomy-tab--active' : ''}`}
              onClick={() => handleTabChange('old')}
            >
              Old Taxonomy
            </button>
          </div>
          <span className="taxonomy-browser-cat-count">{tree.totalCategories} categories</span>
        </div>
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
        <DetailPanel node={selected} totalPois={totalPois} activeTab={activeTab} />
      </div>
    </div>
  );
}
