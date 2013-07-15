from deployer.node import SimpleNode, Node, Env, EnvAction, IsolationIdentifierType, iter_isolations, Action, Group
from deployer.inspection import filters


class PathType:
    """
    Types for displaying the ``Node`` address in a tree.
    It's an options for Inspector.get_path()
    """

    NAME_ONLY = 'NAME_ONLY'
    """
    A list of names.
    """

    NODE_AND_NAME = 'NODE_AND_NAME'
    """
    A list of ``(Node, name)`` tuples.
    """

    NODE_ONLY = 'NODE_ONLY'
    """
    A list of nodes.
    """

class AttributeType:
    PROPERTY = 'PROPERTY'
    QUERY = 'QUERY'
    ACTION = 'ACTION'
    CHILD_NODE = 'CHILD_NODE'
    CONSTANT = 'CONSTANT'


class Inspector(object):
    """
    Introspection of a ``Node`` instance.
    """
    def __init__(self, node):
        if isinstance(node, Env):
            self.env = node
            self.node = node._node
            self.__class__ = _EnvInspector
        elif isinstance(node, Node):
            self.env = None
            self.node = node
        else:
            raise Exception('Expecting a Node or Env instance')

    def __repr__(self):
        return 'Inspector(node=%s)' % self.node.__class__.__name__

    @property
    def is_isolated(self):
        return self.node._node_is_isolated

    def iter_isolations(self, identifier_type=IsolationIdentifierType.INT_TUPLES):
        return iter_isolations(self.node, identifier_type=identifier_type)

    def get_isolation(self, identifier, identifier_type=IsolationIdentifierType.INT_TUPLES):
        for i, node in self.iter_isolations(identifier_type):
            if i == identifier:
                return node
        raise AttributeError('Isolation not found')

    def _filter(self, include_private, filter):
        childnodes = { }
        for name in dir(self.node.__class__):
            if not name.startswith('__') and name != 'parent':
                if include_private or not name.startswith('_'):
                    attr = getattr(self.node, name)
                    if filter(attr):
                        childnodes[name] = attr
        return childnodes

    def get_childnodes(self, include_private=True, verify_parent=True):
        """
        Return a list of childnodes.

        :param include_private: ignore names starting with underscore.
        :type include_private: bool
        :param verify_parent: check that the parent matches the current node.
        :type verify_parent: bool
        """
        # Retrieve all nodes.
        def f(i):
            return isinstance(i, Node) and (not verify_parent or i.parent == self.node)
        nodes = self._filter(include_private, f).values()

        # Order by _node_creation_counter
        return sorted(nodes, key=lambda n: n._node_creation_counter)

    def has_childnode(self, name):
        """
        Returns ``True`` when this node has a childnode called ``name``.
        """
        try:
            self.get_childnode(name)
            return True
        except AttributeError:
            return False

    def get_childnode(self, name):
        """
        Return the childnode with this name or raise ``AttributeError``.
        """
        for c in self.get_childnodes():
            if Inspector(c).get_name() == name:
                return c
        raise AttributeError('Childnode not found.')

    def get_actions(self, include_private=True):
        """
        Return a list of ``Action`` instances for the actions in this node.

        :param include_private: Include actions starting with an underscore.
        :type include_private: bool
        """
        actions = self._filter(include_private, lambda i: isinstance(i, Action) and
                    not i.is_property and not i.is_query)

        # Order alphabetically.
        return sorted(actions.values(), key=lambda a:a._attr_name)

    def has_action(self, name): # TODO: unittest
        """
        Returns ``True`` when this node has an action called ``name``.
        """
        try:
            self.get_action(name)
            return True
        except AttributeError:
            return False

    def get_action(self, name): # TODO: unittest
        """
        Return the ``Action`` with this name or raise ``AttributeError``.
        """
        for a in self.get_actions():
            if a.name == name:
                return a
        raise AttributeError('Action not found.')

    def get_properties(self, include_private=True): # TODO: unittest
        """
        List all the properties. (This are Action instances.)
        """
        # The @property descriptor is in a Node replaced by the
        # node.PropertyDescriptor. This returns an Action object instead of
        # executing it directly.
        return self._filter(include_private, lambda i:
                        isinstance(i, Action) and i.is_property).values()

    def get_property(self, name): # TODO: unittest
        for p in self.get_properties():
            if p.name == name:
                return p
        raise AttributeError('Property not found.')

    def has_property(self, name): # TODO: unittest
        """
        Returns ``True`` when the attribute ``name`` is a @property.
        """
        try:
            self.get_property(name)
            return True
        except AttributeError:
            return False

    def get_queries(self, include_private=True): # TODO: unittest
        # Internal only. For the shell.
        return self._filter(include_private, lambda i:
                    isinstance(i, Action) and i.is_query).values()

    def get_query(self, name): # TODO: unittest
        """
        Returns an Action object that wraps the Query.
        Private because, normally end-user code does not deal with
        Action-instances, because queries appear to be automatically resolved
        during attribute access. And this returns an Action instance.
        """
        for q in self.get_queries():
            if q.name == name:
                return q
        raise AttributeError('Query not found.')

    def has_query(self, name):
        """
        Returns ``True`` when the attribute ``name`` of this node is a Query.
        """
        try:
            self.get_query(name)
            return True
        except AttributeError:
            return False

    def suppress_result_for_action(self, name):
        """
        ``True`` when the ``@suppress_result`` decorator has been used around this action.
        """
        return self.get_action(name).suppress_result

    def get_path(self, path_type=PathType.NAME_ONLY):
        """
        Return a (name1, name2, ...) tuple, defining the path from the root until here.

        :param path_type: Path formatting.
        :type path_type: :class:`.PathType`
        """
        result = []
        n = self.node
        while n:
            if path_type == PathType.NAME_ONLY:
                result.append(Inspector(n).get_name())

            elif path_type == PathType.NODE_AND_NAME:
                result.append((n, Inspector(n).get_name()))

            elif path_type == PathType.NODE_ONLY:
                result.append(n)
            else:
                raise Exception('Invalid path_type')

            n = n.parent

        return tuple(result[::-1])

    def get_root(self):
        """
        Return the root ``Node`` of the tree.
        """
        node = self.node
        while node.parent:
            node = node.parent
        return node

    def get_parent(self): # TODO: unittest!!
        """
        Return the parent ``Node`` or raise ``AttributeError``.
        """
        if self.parent:
            return self.parent
        else:
            raise AttributeError('No parent found. Is this the root node?')

    def get_group(self):
        """
        Return the group to which this node belongs.
        """
        return self.node.node_group or (
                Inspector(self.node.parent).get_group() if self.node.parent else Group())

    def get_name(self):
        """
        Return the name of this node.

        Note: when a node is nested in a parent node, the name becomes the
        attribute name of this node in the parent.
        """
        return self.node._node_name or self.node.__class__.__name__

    def get_full_name(self): #XXX deprecate!!!
        return self.node.__class__.__name__

    def get_isolation_identifier(self):
        return self.node._node_isolation_identifier

    def is_callable(self):
        """
        Return ``True`` when this node implements ``__call__``.
        """
        return hasattr(self.node, '__call__')

    def _walk(self):
        visited = set()
        todo = [ self.node ]

        def key(n):
            # Unique identifier for every node.
            # (The childnode descriptor will return another instance every time.)
            i = Inspector(n)
            return (i.get_root(), i.get_path())

        while todo:
            n = todo.pop(0)
            yield n
            visited.add(key(n))

            for c in Inspector(n).get_childnodes(verify_parent=False):
                if key(c) not in visited:
                    todo.append(c)

    def walk(self, filter=None):
        """
        Recursively walk (topdown) through the nodes and yield them.

        It does not split ``SimpleNodes`` nodes in several isolations.

        :param filter: A :class:`.filters.Filter` instance.
        :returns: A :class:`.NodeIterator` instance.
        """
        return NodeIterator(self._walk).filter(filter)


class _EnvInspector(Inspector):
    """
    When doing the introspection on an Env object, this acts like a proxy and
    makes sure that the result is compatible for in an Env environment.
    """
    def get_childnodes(self, include_private=True):
        nodes = Inspector.get_childnodes(self, include_private)
        return map(self.env._Env__wrap_node, nodes)

    def get_childnode(self, name):
        for c in self.get_childnodes():
            if Inspector(c).get_name() == name:
                return c
        raise AttributeError('Childnode not found.')

    def get_actions(self, include_private=True):
        actions = []
        for a in Inspector.get_actions(self, include_private):
            actions.append(self.env._Env__wrap_action(a))
        return actions

    def iter_isolations(self, *a, **kw):
        for index, node in Inspector.iter_isolations(self, *a, **kw):
            yield index, self.env._Env__wrap_node(node)

    def _walk(self):
        for node in Inspector._walk(self):
            yield self.env._Env__wrap_node(node)

    def _trace_query(self, name):
        """
        Execute this query, but return the QueryResult wrapper instead of the
        actual result. This wrapper contains trace information for debugging.
        """
        action = self.get_query(name)
        query_result = EnvAction(self.env, action)(return_query_result=True)
        return query_result

    def _execute_property(self, name):
        """
        Executes the property in this environment.
        """
        action = self.get_property(name)
        return EnvAction(self.env, action)()


class NodeIterator(object):
    """
    Generator object which yields the nodes in a collection.
    """
    def __init__(self, node_iterator_func):
        self._iterator_func = node_iterator_func

    def __iter__(self):
        return self._iterator_func()

    def __len__(self):
        return sum(1 for _ in self)

    def filter(self, filter):
        """
        Apply filter on this node iterator, and return a new iterator instead.
        `filter` should be a Filter instance.
        """
        if filter is not None:
            assert isinstance(filter, filters.Filter)

            def new_iterator():
                for n in self:
                    if filter._filter(n):
                        yield n
            return NodeIterator(new_iterator)
        else:
            return self

    def prefer_isolation(self, index):
        """
        For nodes that are not yet isoleted. (SimpleNodes, or normal Nodes
        nested in there.) yield the isolations with this index.  Otherwise,
        nodes are yielded unmodified.
        """
        def new_iterator():
            for n in self:
                # When this is a SimpleNode, yield only this isolation if it
                # exists.
                if not n._node_is_isolated:
                    try:
                        yield n[index]
                    except KeyError:
                        # TODO: maybe: yield n here. Not 100% sure, whether this is the best.
                        pass
                # Otherwise, just yield the node.
                else:
                    yield n
        return NodeIterator(new_iterator)

    def call_action(self, name, *a, **kw):
        """
        Call a certain action on all the nodes.
        """
        # Note: This will split the SimpleNode Arrays into their isolations.
        for n in self:
            for index, node in Inspector(n).iter_isolations():
                action = getattr(node, name)
                yield action(*a, **kw)
