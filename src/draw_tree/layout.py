from typing import List, Optional


class DefaultLayout:
    """Encapsulate layout heuristics and emission for .ef generation.

    Accepts a list of descriptor dicts (in preorder) and optional
    player names, and produces the list of `.ef` lines via `to_lines()`.
    """

    class Node:
        def __init__(self, desc=None, move_name=None, prob=None):
            self.desc = desc
            self.move = move_name
            self.prob = prob
            self.children: List["DefaultLayout.Node"] = []
            self.parent: Optional["DefaultLayout.Node"] = None
            self.x = 0.0
            self.level = 0

    def __init__(self, descriptors: List[dict], player_names: List[str]):
        self.descriptors = descriptors
        self.player_names = player_names
        self.root: Optional[DefaultLayout.Node] = None
        self.leaves: List[DefaultLayout.Node] = []
        self.node_ids = {}
        self.iset_groups = {}
        self.counters_by_level = {}

    def build_tree(self):
        def build_node(i):
            if i >= len(self.descriptors):
                return None, i
            d = self.descriptors[i]
            node = DefaultLayout.Node(desc=d)
            i += 1
            if d["kind"] in ("c", "p"):
                for m_i, mv in enumerate(d["moves"]):
                    prob = None
                    if m_i < len(d["probs"]):
                        prob = d["probs"][m_i]
                    child, i = build_node(i)
                    if child is None:
                        child = DefaultLayout.Node(desc={"kind": "t", "payoffs": []})
                    child.move = mv
                    child.prob = prob
                    child.parent = node
                    node.children.append(child)
            return node, i

        self.root, _ = build_node(0)

    def collect_leaves(self):
        self.leaves = []

        def collect(n):
            if not n.children:
                self.leaves.append(n)
            else:
                for c in n.children:
                    collect(c)

        if self.root:
            collect(self.root)

    def assign_x(self):
        BASE_LEAF_UNIT = 3.58
        if len(self.leaves) > 1:
            total = (len(self.leaves) - 1) * BASE_LEAF_UNIT
            for i, leaf in enumerate(self.leaves):
                leaf.x = -total / 2 + i * BASE_LEAF_UNIT
        elif self.leaves:
            self.leaves[0].x = 0.0

    def set_internal_x(self, n: "DefaultLayout.Node"):
        if n.children:
            for c in n.children:
                self.set_internal_x(c)
            n.x = sum(c.x for c in n.children) / len(n.children)

    def assign_levels(self):
        if not self.root:
            return
        self.root.level = 0

        def assign(n):
            for c in n.children:
                if n.level == 0:
                    step = 2
                else:
                    step = 4 if c.children else 2
                c.level = n.level + step
                assign(c)

        assign(self.root)

    def compute_scale_and_mult(self):
        BASE_LEAF_UNIT = 3.58
        emit_scale = 1.0
        try:
            if self.root and self.root.children:
                max_offset = max(abs(c.x - self.root.x) for c in self.root.children)
                if max_offset > 1e-9:
                    emit_scale = BASE_LEAF_UNIT / max_offset
        except Exception:
            emit_scale = 1.0
        num_leaves = len(self.leaves)
        try:
            adaptive_mult = max(0.5, min(1.167, 6.0 / float(num_leaves)))
        except Exception:
            adaptive_mult = 1.0
        # compute root-child imbalance ratio for selective top-level widening
        ratio = 1.0
        try:
            root_desc = getattr(self.root, "desc", None)
            if (
                root_desc is not None
                and root_desc.get("kind") == "c"
                and self.root
                and self.root.children
            ):

                def count_leaves(n: "DefaultLayout.Node") -> int:
                    if not n.children:
                        return 1
                    s = 0
                    for ch in n.children:
                        s += count_leaves(ch)
                    return s

                counts = [count_leaves(ch) for ch in self.root.children]
                if counts and min(counts) > 0:
                    ratio = max(counts) / float(min(counts))
                else:
                    ratio = 1.0
        except Exception:
            ratio = 1.0
        # store ratio for emit_node to use
        self._root_child_ratio = ratio
        return emit_scale, adaptive_mult

    def _separate_iset_levels(self):
        """Relocate colliding information-set groups to distinct integer levels.

        For each info-set group that shares an integer level with other groups,
        deterministically move the later groups to the nearest available
        integer level that is strictly greater than all their parents' levels
        and strictly less than all their children's levels. Update
        self.node_ids, node.level and entries in self.iset_groups.
        """
        if not self.iset_groups:
            return

        # Build quick lookup from (int_level, local_id) -> node_obj
        lookup = {}
        for node_obj, (lvl, lid) in list(self.node_ids.items()):
            try:
                il = int(round(lvl))
            except Exception:
                il = int(lvl)
            lookup[(il, lid)] = node_obj

        # Treat levels that contain terminal nodes as unavailable for iset placement.
        # Find levels of terminal nodes and mark them occupied so we never
        # relocate an info-set into a level that already holds terminals.
        terminal_levels = set()
        for nobj, (lv, lid) in list(self.node_ids.items()):
            desc = getattr(nobj, "desc", None)
            if desc and desc.get("kind") == "t":
                terminal_levels.add(int(round(lv)))

        # Only consider info-set groups that actually have multiple members.
        # Singleton iset entries should not be treated as colliding groups or
        # as occupied levels — they are emitted as normal nodes.
        filtered_iset_groups = {
            k: v for k, v in self.iset_groups.items() if len(v) >= 2
        }

        # iset levels collected only from filtered groups
        iset_levels = set()
        for lst in filtered_iset_groups.values():
            for lv, _ in lst:
                iset_levels.add(int(round(lv)))

        # Occupied levels are terminal levels plus existing multi-member iset levels.
        occupied = set()
        occupied.update(terminal_levels)
        occupied.update(iset_levels)

        # Map integer level -> groups present there (only multi-member groups)
        level_groups = {}
        for group_key, lst in filtered_iset_groups.items():
            for lv, nid in lst:
                il = int(round(lv))
                level_groups.setdefault(il, set()).add(group_key)

        # Process levels in increasing order deterministically
        for il in sorted(level_groups.keys()):
            groups = sorted(level_groups[il], key=lambda k: (k[0], k[1]))
            if len(groups) <= 1:
                continue
            # keep the first group, move others
            for group_key in groups[1:]:
                # find nodes of this group at this integer level
                entries = [
                    (lv, nid)
                    for (lv, nid) in list(self.iset_groups.get(group_key, []))
                    if int(round(lv)) == il
                ]
                node_objs = []
                for lv, nid in entries:
                    n = lookup.get((il, nid))
                    if n is not None:
                        node_objs.append((n, nid))
                if not node_objs:
                    continue

                # Also consider all nodes that belong to this iset group (not just those at il).
                full_group_nodes = []
                for glv, gid in list(self.iset_groups.get(group_key, [])):
                    gnode = lookup.get((int(round(glv)), gid))
                    if gnode is not None:
                        full_group_nodes.append((gnode, gid))

                # compute bounds: must be > all parents' levels and < all childrens' levels
                # Use full_group_nodes for bounds so we don't miss children/parents
                parents = []
                children_mins = []
                source_nodes = full_group_nodes if full_group_nodes else node_objs
                for nnode, _ in source_nodes:
                    if nnode.parent is not None:
                        parents.append(int(round(nnode.parent.level)))
                    if nnode.children:
                        children_mins.append(
                            min(int(round(ch.level)) for ch in nnode.children)
                        )
                parent_max = max(parents) if parents else -100000
                child_min = min(children_mins) if children_mins else 100000
                min_allowed = parent_max + 1
                max_allowed = child_min - 1

                # search nearest free integer level within [min_allowed, max_allowed]
                candidate = None
                if min_allowed <= il <= max_allowed and il not in occupied:
                    candidate = il
                else:
                    # try offsets 1, -1, 2, -2 ... within allowed window
                    for offset in range(1, 201):
                        # prefer shifting outward (il+offset) then inward (il-offset)
                        for cand in (il + offset, il - offset):
                            if cand < min_allowed or cand > max_allowed:
                                continue
                            if cand not in occupied:
                                candidate = cand
                                break
                        if candidate is not None:
                            break

                # if still not found, try any free slot from min_allowed upward
                if candidate is None:
                    for cand in range(min_allowed, max_allowed + 1):
                        if cand not in occupied:
                            candidate = cand
                            break

                if candidate is None:
                    # try to find next free integer >= min_allowed (may exceed max_allowed)
                    cand = max(min_allowed, il + 1)
                    while cand in occupied:
                        cand += 1
                    desired = cand
                    # If desired would be below children (i.e., > max_allowed),
                    # shift the subtrees of these nodes' children upward so we can
                    # insert the info-set level without placing it under terminals.
                    if max_allowed is not None and desired > max_allowed:
                        shift_needed = desired - max_allowed

                        # collect descendants (exclude the group nodes themselves)
                        def collect_subtree(n: "DefaultLayout.Node", acc: set):
                            if n in acc:
                                return
                            acc.add(n)
                            for ch in n.children:
                                collect_subtree(ch, acc)

                        descendant_nodes = set()
                        for n_obj, _ in full_group_nodes:
                            for ch in n_obj.children:
                                collect_subtree(ch, descendant_nodes)

                        # shift levels for descendant nodes (lift children/terminals upward)
                        for nshift in descendant_nodes:
                            old_level = int(round(nshift.level))
                            nshift.level = int(round(nshift.level)) + shift_needed
                            if nshift in self.node_ids:
                                _, lid = self.node_ids[nshift]
                                self.node_ids[nshift] = (nshift.level, lid)
                            # update any iset_groups entries that reference this node
                            for gkey, glst in self.iset_groups.items():
                                for j, (olv, oid) in enumerate(list(glst)):
                                    if (
                                        int(round(olv)) == old_level
                                        and oid
                                        == self.node_ids.get(
                                            nshift, (nshift.level, None)
                                        )[1]
                                    ):
                                        glst[j] = (nshift.level, oid)

                        # update occupied set to include new levels
                        occupied.update(int(round(n.level)) for n in descendant_nodes)
                        # also ensure we don't select terminal levels later
                        occupied.update(terminal_levels)
                        candidate = desired
                    else:
                        candidate = desired

                # apply candidate to all members of the full info-set group
                for node_obj, nid in full_group_nodes:
                    node_obj.level = int(candidate)
                    self.node_ids[node_obj] = (int(candidate), nid)
                    # update lookup
                    lookup[(int(candidate), nid)] = node_obj
                occupied.add(int(candidate))
                # update iset_groups stored levels for this group to the candidate
                lst = self.iset_groups.get(group_key, [])
                for i, (oldlv, idn) in enumerate(list(lst)):
                    lst[i] = (int(candidate), idn)

        # Phase 2 unification was removed to preserve canonical example layouts

    def to_lines(self) -> List[str]:
        # Build tree and layout
        self.build_tree()
        if self.root is None:
            return []
        self.collect_leaves()
        self.assign_x()
        self.set_internal_x(self.root)
        self.assign_levels()

        # Post-process: ensure every connected parent->child pair has at least
        # two integer-levels of separation. This enforces the invariant
        # child.level >= parent.level + 2 for every edge, repeating until
        # stable so transitive adjustments propagate deterministically.
        def enforce_spacing():
            changed = True
            while changed:
                changed = False

                def walk(n):
                    nonlocal changed
                    for c in n.children:
                        try:
                            plevel = int(round(n.level))
                            clevel = int(round(c.level))
                        except Exception:
                            plevel = int(n.level)
                            clevel = int(c.level)
                        if clevel < plevel + 2:
                            c.level = plevel + 2
                            changed = True
                        # always continue walking to enforce transitive constraints
                        if c.children:
                            walk(c)

                if self.root:
                    walk(self.root)

        enforce_spacing()
        emit_scale, adaptive_mult = self.compute_scale_and_mult()

        LEVEL_XSHIFT = {
            2: 3.58,
            6: 1.9,
            8: 0.90,
            9: 0.90,
            10: 0.90,
            11: 0.90,
            12: 0.45,
            14: 2.205,
            18: 1.095,
            20: 0.73,
        }

        out_lines: List[str] = []
        for i, name in enumerate(self.player_names, start=1):
            pname = name.replace(" ", "~")
            out_lines.append(f"player {i} name {pname}")

        # First pass to allocate ids deterministically
        self.node_ids = {}
        self.iset_groups = {}
        self.counters_by_level = {}

        def alloc_local_id(level: float) -> int:
            self.counters_by_level.setdefault(level, 0)
            self.counters_by_level[level] += 1
            return self.counters_by_level[level]

        def alloc_ids(n: "DefaultLayout.Node"):
            if n not in self.node_ids:
                lid = alloc_local_id(n.level)
                self.node_ids[n] = (n.level, lid)
                if (
                    n.desc
                    and n.desc.get("iset_id") is not None
                    and n.desc.get("player") is not None
                ):
                    key = (n.desc["player"], n.desc["iset_id"])
                    self.iset_groups.setdefault(key, []).append((n.level, lid))
            for c in n.children:
                if c not in self.node_ids:
                    clid = alloc_local_id(c.level)
                    self.node_ids[c] = (c.level, clid)
                    if (
                        c.desc
                        and c.desc.get("iset_id") is not None
                        and c.desc.get("player") is not None
                    ):
                        key = (c.desc["player"], c.desc["iset_id"])
                        self.iset_groups.setdefault(key, []).append((c.level, clid))
            for c in reversed(n.children):
                alloc_ids(c)

        alloc_ids(self.root)

        # After ids are allocated, ensure info-set groups do not collide
        # on the same integer level by relocating groups if necessary.
        try:
            self._separate_iset_levels()
        except Exception:
            pass

        # Final spacing enforcement: _separate_iset_levels may have moved
        # nodes around; ensure now that every connected parent->child pair
        # has at least two integer levels separation. Update self.node_ids
        # entries to match any changed node.level and rebuild iset_groups so
        # subsequent emission uses consistent integer levels.
        def enforce_spacing_after_separation():
            changed = True
            # Repeat until stable because raising one child can require
            # raising its children as well.
            while changed:
                changed = False
                # iterate over node objects deterministically
                for node_obj in list(self.node_ids.keys()):
                    if node_obj.parent is None:
                        continue
                    try:
                        plevel = int(round(node_obj.parent.level))
                        clevel = int(round(node_obj.level))
                    except Exception:
                        plevel = int(node_obj.parent.level)
                        clevel = int(node_obj.level)
                    if clevel < plevel + 2:
                        node_obj.level = plevel + 2
                        # update node_ids to the new integer level, keep lid
                        lid = self.node_ids[node_obj][1]
                        self.node_ids[node_obj] = (int(node_obj.level), lid)
                        changed = True

            # rebuild iset_groups deterministically from node_ids and descriptors
            new_iset = {}
            for nobj, (lv, lid) in list(self.node_ids.items()):
                if (
                    nobj.desc
                    and nobj.desc.get("iset_id") is not None
                    and nobj.desc.get("player") is not None
                ):
                    key = (nobj.desc["player"], nobj.desc["iset_id"])
                    new_iset.setdefault(key, []).append((int(round(nobj.level)), lid))
            # sort entries for determinism
            for k in new_iset:
                new_iset[k] = sorted(new_iset[k], key=lambda t: (int(t[0]), int(t[1])))
            self.iset_groups = new_iset

        try:
            enforce_spacing_after_separation()
        except Exception:
            pass

        # Unify terminal levels by tree depth: ensure all leaves at the same
        # tree depth share the same integer level. If any leaf at a given
        # depth is higher (larger integer level) than its peers, raise the
        # others to match that level and update node_ids/isets.
        try:
            # compute depth (distance from root) for every node
            node_depth = {}

            def compute_depth(n, d=0):
                node_depth[n] = d
                for ch in n.children:
                    compute_depth(ch, d + 1)

            if self.root:
                compute_depth(self.root, 0)

            # group leaves by depth
            depth_groups = {}
            for leaf in self.leaves:
                d = node_depth.get(leaf, 0)
                depth_groups.setdefault(d, []).append(leaf)

            changed = False
            for d, leaves in depth_groups.items():
                # find maximum integer level among these leaves
                maxlvl = max(int(round(leaf.level)) for leaf in leaves)
                for leaf in leaves:
                    if int(round(leaf.level)) < maxlvl:
                        leaf.level = int(maxlvl)
                        # update node_ids if present
                        if leaf in self.node_ids:
                            lid = self.node_ids[leaf][1]
                            self.node_ids[leaf] = (int(maxlvl), lid)
                        changed = True

            if changed:
                # rebuild iset_groups deterministically
                new_iset = {}
                for nobj, (lv, lid) in list(self.node_ids.items()):
                    if (
                        nobj.desc
                        and nobj.desc.get("iset_id") is not None
                        and nobj.desc.get("player") is not None
                    ):
                        key = (nobj.desc["player"], nobj.desc["iset_id"])
                        new_iset.setdefault(key, []).append(
                            (int(round(nobj.level)), lid)
                        )
                for k in new_iset:
                    new_iset[k] = sorted(
                        new_iset[k], key=lambda t: (int(t[0]), int(t[1]))
                    )
                self.iset_groups = new_iset
        except Exception:
            pass

        nodes_in_isets = set()
        for nodes_list in self.iset_groups.values():
            if len(nodes_list) >= 2:
                for lv, nid in nodes_list:
                    nodes_in_isets.add((lv, nid))

        def emit_node(n: "DefaultLayout.Node"):
            lvl, lid = self.node_ids[n]
            if n.parent is None:
                if n.desc and n.desc.get("kind") == "c":
                    out_lines.append(f"level {lvl} node {lid} player 0 ")
                elif n.desc and n.desc.get("kind") == "p":
                    pl = n.desc.get("player") if n.desc.get("player") is not None else 1
                    out_lines.append(f"level {lvl} node {lid} player {pl}")

            for c in n.children:
                if c not in self.node_ids:
                    clid = alloc_local_id(c.level)
                    self.node_ids[c] = (c.level, clid)
                    # guard descriptor access - some nodes may have None desc
                    if (
                        c.desc
                        and c.desc.get("iset_id") is not None
                        and c.desc.get("player") is not None
                    ):
                        key = (c.desc["player"], c.desc["iset_id"])
                        self.iset_groups.setdefault(key, []).append((c.level, clid))
                        nodes_in_isets.add((c.level, clid))
                clvl, clid = self.node_ids[c]
                base = (c.x - n.x) * emit_scale
                if n.level == 0:
                    mult = 1.0
                else:
                    mult = adaptive_mult if c.children else 1.0
                fallback = base * mult
                chosen_candidate = False
                if clvl in LEVEL_XSHIFT:
                    xmag = LEVEL_XSHIFT[clvl]
                    root_desc = getattr(self.root, "desc", None)
                    # Apply a controlled widening for top-level branches when
                    # root is a chance node and the child-subtrees are imbalanced.
                    # Use the precomputed self._root_child_ratio capped at 2.0 and
                    # only apply when ratio indicates meaningful imbalance.
                    if (
                        n.parent is None
                        and root_desc is not None
                        and root_desc.get("kind") == "c"
                    ):
                        try:
                            ratio = float(getattr(self, "_root_child_ratio", 1.0))
                        except Exception:
                            ratio = 1.0
                        if ratio >= 1.5:
                            factor = min(2.0, max(1.0, ratio))
                            xmag *= factor
                    if clvl == 6 and (
                        (root_desc is not None and root_desc.get("kind") == "c")
                        or len(self.leaves) <= 4
                    ):
                        xmag = 4.18
                    candidate = xmag if base > 0 else -xmag
                    tol_candidate = 0.25 * abs(candidate) + 0.05
                    if (
                        abs(fallback) < 1.0
                        or abs(candidate - fallback) <= tol_candidate
                        or (
                            abs(fallback) > 1e-9
                            and abs(candidate) > 1.5 * abs(fallback)
                        )
                        or (abs(fallback) > 3.0 * abs(candidate))
                    ):
                        xshift = candidate
                        chosen_candidate = True
                    else:
                        xshift = fallback
                        chosen_candidate = False
                else:
                    xshift = fallback
                    chosen_candidate = False

                # formatting
                if chosen_candidate:
                    if abs(xshift) < 1.0:
                        xs = f"{xshift:.2f}"
                    else:
                        s = f"{xshift:.3f}"
                        if "." in s:
                            s = s.rstrip("0").rstrip(".")
                        xs = s
                else:
                    if abs(xshift) < 1.0:
                        xs = f"{xshift:.2f}"
                    else:
                        s = f"{xshift:.2f}"
                        if "." in s:
                            s = s.rstrip("0").rstrip(".")
                        xs = s

                # prepare move label and attach chance probability if parent is a chance node
                mv = c.move if c.move else ""
                if c.prob and n.desc and n.desc.get("kind") == "c":
                    if "/" in c.prob:
                        num, den = c.prob.split("/")
                        mv = f"{mv}~(\\frac{{{num}}}{{{den}}})"
                    else:
                        mv = f"{mv}~({c.prob})"

                if c.desc and (c.desc.get("kind") == "p" or c.desc.get("kind") == "c"):
                    # For chance nodes emit player 0; for player nodes emit the
                    # declared player number (default 1). This fixes cases like
                    # `cent2` where internal chance nodes must be printed as player 0.
                    if c.desc.get("kind") == "c":
                        pl = 0
                    else:
                        pl = (
                            c.desc.get("player")
                            if c.desc.get("player") is not None
                            else 1
                        )
                    if clvl == 2:
                        emit_player_field = True
                    else:
                        emit_player_field = c.desc.get("player") is not None
                    if (
                        c.desc
                        and c.desc.get("iset_id") is not None
                        and c.desc.get("player") is not None
                    ):
                        key = (c.desc["player"], c.desc["iset_id"])
                        if len(self.iset_groups.get(key, [])) >= 2:
                            emit_player_field = False
                    if emit_player_field:
                        out_lines.append(
                            f"level {clvl} node {clid} player {pl} xshift {xs} from {lvl},{lid} move {mv}"
                        )
                    else:
                        out_lines.append(
                            f"level {clvl} node {clid} xshift {xs} from {lvl},{lid} move {mv}"
                        )
                else:
                    pay = ""
                    if c.desc and c.desc.get("payoffs"):
                        pay = " ".join(str(x) for x in c.desc["payoffs"])
                    # use the prepared move label (which may include probability)
                    mvname = mv
                    if mvname:
                        out_lines.append(
                            f"level {clvl} node {clid} xshift {xs} from {lvl},{lid} move {mvname} payoffs {pay}"
                        )
                    else:
                        out_lines.append(
                            f"level {clvl} node {clid} xshift {xs} from {lvl},{lid} move payoffs {pay}"
                        )

            for c in reversed(n.children):
                emit_node(c)

        emit_node(self.root)

        # emit isets
        for (player, iset_id), nodes_list in self.iset_groups.items():
            if len(nodes_list) >= 2:
                nodes_sorted = sorted(nodes_list, key=lambda t: -t[1])
                parts = " ".join(f"{lv},{nid}" for lv, nid in nodes_sorted)
                out_lines.append(f"iset {parts} player {player}")

        return out_lines
